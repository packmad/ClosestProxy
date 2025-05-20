import argparse
import json
import multiprocessing
import requests
import socket
import sys
import tempfile
import time

from dataclasses import dataclass
from ipaddress import ip_network
from typing import List, Optional, Dict, Set
from tqdm import tqdm
from pathlib import Path
from os.path import join, isfile


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


@dataclass
class Geolocation:
    country: str
    city: Optional[str]

@dataclass
class ProxyInfo:
    proxy: str
    protocol: str
    ip: str
    port: int
    https: bool
    anonymity: str
    score: int
    ping: float  # infinity for failed connections
    geolocation: Geolocation
    works: bool


def get_url(url: str, proxy: Optional[ProxyInfo] = None) -> Optional[str]:
    try:
        proxies: Optional[dict[str, str]] = None
        if proxy is not None:
            proto = proxy.protocol.lower()

            if proto in {"socks5", "socks4"}:
                proxy_uri = f"{proto}://{proxy.ip}:{proxy.port}"
                proxies = {"http": proxy_uri, "https": proxy_uri}
            elif proto == "http":
                proxy_uri = f"http://{proxy.ip}:{proxy.port}"
                proxies = {"http": proxy_uri}
            elif proto == 'https':
                proxy_uri = f"https://{proxy.ip}:{proxy.port}"
                proxies = {"https": proxy_uri}
            else:
                raise ValueError(f"Unsupported proxy protocol: {proxy.protocol!r}")
        resp = requests.get(url, proxies=proxies, timeout=16)
        if resp.ok:
            return resp.text
    except Exception as e:
        eprint(e)
    return None


def geolocation_service(proxy: Optional[ProxyInfo] = None) -> Optional[str]:
    r = get_url("https://ipinfo.io/json", proxy)
    if r is None:
        return None
    return json.loads(r)["country"]


def does_it_work(proxy: ProxyInfo) -> bool:
    # Assumption: the Tor Project does not block proxies :)
    r = get_url('https://www.torproject.org/', proxy)
    if r is None:
        return False
    return 'Tor Project' in r


def _socks4_handshake(sock: socket.socket) -> bool:
    """
    SOCKS 4/4a: CONNECT 1.1.1.1:80 (any public IP works)
    Success reply → VN=0x00 or 0x04 (impls differ), CD=0x5A.
    """
    dst_ip   = b"\x01\x01\x01\x01"         # 1.1.1.1
    dst_port = (80).to_bytes(2, "big")     # port 80
    payload  = b"\x04\x01" + dst_port + dst_ip + b"\x00"  # USERID empty
    sock.sendall(payload)
    reply = sock.recv(8)
    return len(reply) >= 2 and reply[1] == 0x5A            # 0x5A = granted


def _socks5_handshake(sock: socket.socket) -> bool:
    """
    SOCKS 5:  no-auth negotiation only (0x05 0x01 0x00).
    Expect 0x05 0x00 back.
    """
    sock.sendall(b"\x05\x01\x00")
    reply = sock.recv(2)
    return reply == b"\x05\x00"


def _http_probe(sock: socket.socket) -> bool:
    """
    HTTP proxy: send the lightest legal request (OPTIONS * ...).
    A valid proxy will return an HTTP status line.
    """
    sock.sendall(
        b"OPTIONS * HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Connection: close\r\n\r\n"
    )
    reply = sock.recv(1024)  # 1 KiB is plenty for the tiny handshake responses expected
    return reply.startswith(b"HTTP/1.")


def test_proxy(proxy: ProxyInfo) -> ProxyInfo:
    """
    Populate proxy.ping (in seconds) if the proxy answers its handshake.
    If it succeeds, then it makes a real request and sets proxy.works if it works out.
    On failure, proxy.ping and proxy.works are left untouched.
    """
    handlers = {
        "socks5": _socks5_handshake,
        "socks4": _socks4_handshake,
        "http":   _http_probe,
        "https":  _http_probe,  # HTTPS proxies behave the same for CONNECT
    }
    handshake = handlers.get(proxy.protocol.lower())
    if handshake is None:
        raise ValueError(f"Unsupported proxy protocol: {proxy.protocol!r}")

    try:
        with socket.create_connection((proxy.ip, int(proxy.port)), timeout=8) as sock:
            start = time.time()
            if handshake(sock):
                proxy.ping = time.time() - start
                proxy.works = does_it_work(proxy)
    except (socket.timeout, ConnectionError, OSError):
        pass
    return proxy


def get_data() -> Dict:
    file_path = join(tempfile.gettempdir(), 'data.json')
    if not isfile(file_path):
        r = requests.get('https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.json')
        with open(file_path, 'wb') as fp:
            fp.write(r.content)
            return json.loads(r.content)
    with open(file_path) as fp:
        return json.load(fp)


def parse_data() -> List[ProxyInfo]:
    raw_list = get_data()
    proxy_list: List[ProxyInfo] = list()
    for item in raw_list:
        proxy = ProxyInfo(
            proxy=item['proxy'],
            protocol=item['protocol'],
            ip=item['ip'],
            port=item['port'],
            https=item['https'],
            anonymity=item['anonymity'],
            score=item['score'],
            ping=float('inf'),
            geolocation=Geolocation(**item['geolocation']),
            works=False
        )
        proxy_list.append(proxy)
    return proxy_list


def pretty_print_results(proxies: List[ProxyInfo]) -> None:
    headers = ["Proxy", "Protocol", "IP", "Port", "Ping (s)", "Country", "City"]
    rows = []
    for p in proxies:
        rows.append([
            p.proxy,
            p.protocol,
            p.ip,
            p.port,
            f"{p.ping:.3f}",
            p.geolocation.country,
            p.geolocation.city or "-"
        ])

    # Determine column widths
    col_widths = [max(len(str(cell)) for cell in [header] + [row[i] for row in rows]) for i, header in enumerate(headers)]

    def format_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    print(format_row(headers))
    print("-+-".join("-" * w for w in col_widths))
    for row in rows:
        print(format_row(row))


def main(two_letter_country_codes: Optional[Set[str]] = None, netmask: Optional[int] = None):
    if two_letter_country_codes is None:
        two_letter_country_codes = {geolocation_service()}

    data = [d for d in parse_data() if d.geolocation.country in two_letter_country_codes]
    print(f'> Found {len(data)} proxies in {two_letter_country_codes}')

    with multiprocessing.Pool() as pool:
        results: List[ProxyInfo] = list(tqdm(pool.imap(test_proxy, data), total=len(data)))
    results = [r for r in results if r.works and r.ping != float('inf')]
    results.sort(key=lambda x: x.ping)
    print(f'> Found {len(results)} working proxies')

    if netmask is not None:
        seen = set()
        deduped: List[ProxyInfo] = list()
        for r in results:
            subnet = ip_network(f"{r.ip}/{netmask}", strict=False)
            if subnet not in seen:
                seen.add(subnet)
                deduped.append(r)
        print(f'> Filtered by {netmask=} -> {len(deduped)} left')
        results = deduped

    pretty_print_results(results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Probe proxies for the given country codes."
    )
    parser.add_argument(
        "-c", "--country",
        dest="countries",
        nargs="+",
        metavar="CC",
        help="ISO-3166 2-letter country code(s) (e.g., GB IT US). "
             "If omitted, the script uses your current geolocation."
    )
    parser.add_argument(
        "-s", "--subnet", dest="subnet", type=int, metavar="MASK",
        help="CIDR subnet mask length to deduplicate proxies "
             "(e.g. 24 for /24). Omit for no subnet filtering."
    )
    args = parser.parse_args()
    if args.subnet is not None and not (0 <= args.subnet <= 32):
        parser.error("Subnet mask length must be between 0 and 32")
    if args.countries:
        codes = {cc.upper() for cc in args.countries}
        for cc in codes:
            if len(cc) != 2:
                parser.error(f"'{cc}' is not a 2-letter country code")
        main(codes, args.subnet)
    else:
        main(netmask=args.subnet)
