import json
import multiprocessing
import requests
import socket
import sys
import time

from dataclasses import dataclass
from typing import List, Optional, Dict
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
    geo_service: Optional[str]


def geolocation_service(proxy: Optional[ProxyInfo] = None) -> Optional[str]:
    """
    Ask ifconfig.co for the country ISO code, optionally through a proxy.

    Returns
    -------
    str | None
        Two-letter ISO country code (e.g. “FR”) or None on error/timeout.
    """
    url = "http://ifconfig.co/json"
    try:
        proxies: Optional[dict[str, str]] = None
        if proxy is not None:
            proto = proxy.protocol.lower()

            if proto in {"socks5", "socks4"}:
                scheme = proto
            elif proto in {"http", "https"}:
                scheme = proto
            else:
                raise ValueError(f"Unsupported proxy protocol: {proxy.protocol!r}")
            proxy_uri = f"{scheme}://{proxy.ip}:{proxy.port}"
            proxies = {"http": proxy_uri, "https": proxy_uri}

        resp = requests.get(url, proxies=proxies, timeout=5)
        if resp.ok:
            return resp.json().get("country_iso")

    except Exception as exc:               # network errors, JSON errors, …
        eprint(exc)
    return None



def _socks4_handshake(sock: socket.socket) -> bool:
    """
    SOCKS 4/4a:  CONNECT 1.1.1.1:80  (any public IP works – we just need a
    syntactically-valid request).
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
    HTTP proxy: send the lightest legal request we can (OPTIONS * …).
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
    On failure, proxy.ping is left untouched.
    """
    handlers = {
        "socks5": _socks5_handshake,
        "socks4": _socks4_handshake,
        "http":   _http_probe,
        "https":  _http_probe,      # HTTPS proxies behave the same for CONNECT
    }

    handshake = handlers.get(proxy.protocol.lower())
    if handshake is None:
        raise ValueError(f"Unsupported proxy protocol: {proxy.protocol!r}")

    try:
        with socket.create_connection((proxy.ip, int(proxy.port)), timeout=5) as sock:
            start = time.time()
            if handshake(sock):
                proxy.ping = time.time() - start
                proxy.geo_service = geolocation_service(proxy)
    except (socket.timeout, ConnectionError, OSError):
        pass
    return proxy


def get_data() -> Dict:
    file_path = join(Path.cwd(), 'data.json')
    if not isfile(file_path):
        r = requests.get('https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.json')
        with open(file_path, 'wb') as fp:
            fp.write(r.content)
            return json.loads(r.content)
    with open(file_path) as fp:
        return json.load(fp)


def parse_data() -> List[ProxyInfo]:
    raw_list = get_data()
    proxy_list: List[ProxyInfo] = []
    for item in raw_list:
        geo = Geolocation(**item['geolocation'])
        proxy = ProxyInfo(
            proxy=item['proxy'],
            protocol=item['protocol'],
            ip=item['ip'],
            port=item['port'],
            https=item['https'],
            anonymity=item['anonymity'],
            score=item['score'],
            ping=float('inf'),
            geolocation=geo,
            geo_service=None
        )
        proxy_list.append(proxy)
    return proxy_list


def main():
    your_country = geolocation_service()
    data = [d for d in parse_data() if d.geolocation.country == your_country]
    print(f'Found {len(data)} proxies in your country --> {your_country}')

    with multiprocessing.Pool() as pool:
        results: List[ProxyInfo] = list(tqdm(pool.imap(test_proxy, data), total=len(data)))
    results = [r for r in results if r.ping != float('inf')]
    results.sort(key=lambda x: x.ping)
    print(f'Found {len(results)} working proxies:')
    for p in results:
        print(p)


if __name__ == '__main__':
    main()
