import socket
import time
import multiprocessing
import requests
import sys
import json
from typing import List, Optional
from tqdm import tqdm
from pathlib import Path
from os.path import join, isfile

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class Proxy:
    ip: str
    port: int
    distance: float
    country: Optional[str]

    def __init__(self, proxy: str):
        proxy_ip, proxy_port = proxy.split(':')
        self.ip = proxy_ip
        self.port = proxy_port
        self.distance = test_proxy(proxy)
        self.country = None

    def __str__(self):
        return f'[{round(self.distance, 3)} ms] {self.ip}:{self.port}'

    def toJson(self) -> str:
        return json.dumps(vars(self))

    def geolocation(self):
        if self.country is None:
            proxy = {
                'http': f'socks5://{self.ip}:{self.port}',
            }
            try:
                response = requests.get('http://ifconfig.co/json', proxies=proxy)
                #response = requests.get('http://ifconfig.co/json')
                if response.status_code == 200:
                    self.country = response.json()["country_iso"]
            except Exception as e:
                eprint(e)
        return self.country


def test_proxy(proxy: str) -> float:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Timeout after 5 seconds
        proxy_ip, proxy_port = proxy.split(':')
        start_time = time.time()
        sock.connect((proxy_ip, int(proxy_port)))
        sock.sendall(b'\x05\x01\x00')
        response = sock.recv(2)
        response_time = time.time() - start_time
        sock.close()
        if response == b'\x05\x00':
            return response_time
    except (socket.timeout, ConnectionRefusedError) as e:
        pass
    return float('inf')  # Return infinity for failed connections


def proxy_factory(proxy) -> Proxy:
    return Proxy(proxy)


def find_closest_proxy(file_path) -> List:
    with open(file_path, 'r') as file:
        proxies = file.read().splitlines()

    with multiprocessing.Pool() as pool:
        results: List[Proxy] = list(tqdm(pool.imap(proxy_factory, proxies), total=len(proxies), desc="Testing Proxies"))

    results.sort(key=lambda x: x.distance)
    return results


if __name__ == '__main__':
    file_path = join(Path.cwd(), 'PROXY-List', 'socks5.txt')
    if not isfile(file_path):
        r = requests.get('https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt')
        open(file_path, 'wb').write(r.content)
    assert isfile(file_path)

    closest_proxy = find_closest_proxy(file_path)

    for i, p in enumerate(closest_proxy):
        p: Proxy
        if p.distance != float('inf'):
            print(f'[{p.geolocation()}]', p)
            print(p.toJson())
            if i > 10: break
