from main import ProxyInfo, Geolocation, test_proxy, get_url


def ProxyInfo_builder(ip: str, port: int, protocol: str) -> ProxyInfo:
    pi = ProxyInfo(
        proxy=f"{protocol}://{ip}:{port}",
        protocol=protocol,
        ip=ip,
        port=port,
        https=protocol == 'https',
        anonymity='unknown',
        score=0,
        ping=float('inf'),
        geolocation=Geolocation(
            country='unknown',
            city='unknown'
        ),
        works=False
    )
    return test_proxy(pi)


if __name__ == '__main__':
    pi = ProxyInfo_builder('127.0.0.1', 8080, 'http')
    assert pi.works
    test_url = 'https://ifconfig.co/json'
    res = get_url(test_url, pi)
    print('> With proxy:', res)
    res = get_url(test_url)
    print('> Without proxy:', res)
