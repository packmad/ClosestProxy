# ClosestProxy

A tiny, no‑frills tool that **discovers free public proxies in your own country and benchmarks them in parallel**.  
It pulls a fresh list from Proxifly, filters it by geolocation, hand‑shakes each proxy (SOCKS 4/5 or HTTP/S) and prints the fastest working endpoints.

---

## ✨ Features

| Capability | Details                                                                                                          |
|------------|------------------------------------------------------------------------------------------------------------------|
| **Auto‑fetch list** | Downloads <https://github.com/proxifly/free-proxy-list> on first run and caches it as `data.json`.               |
| **Smart geofilter** | Uses `ifconfig.co` to detect *your* country and keeps only same‑country proxies (lower latency, fewer captchas). |
| **Multi‑process benchmark** | Spawns a `multiprocessing.Pool` so every CPU core dials proxies concurrently.                                    |
| **Protocol aware** | Custom handshake routines for **SOCKS5, SOCKS4/4a, HTTP and HTTPS CONNECT**.                                     |
| **Ping metric** | Measures time to a successful handshake and sorts the winners.                                                   |
| **Single‑file core** | Only one Python file – `main.py` – no frameworks to fight with.                                                  |

---

## 📦 Installation

```bash
# 1. Clone the repo
$ git clone https://github.com/your‑user/proxy‑benchmark.git && cd proxy‑benchmark

# 2. Create a virtualenv (recommended)
$ python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install runtime deps
$ pip install -r requirements.txt
# or, if you don’t use a requirements file:
$ pip install requests tqdm
```

---

## 🚀 Usage

```bash
$ python3 main.py
Found 67 proxies in your country --> FR
100%|████████████████████| 67/67 [00:06<00:00, 11.15it/s]
Found 18 working proxies:
ProxyInfo(proxy='123.123.0.42:1080', protocol='socks5', ping=0.146, ...)
...
```

That’s it! By default the script:

1. Detects your external IP’s country.
2. Parses the latest Proxifly proxy list.
3. Keeps only same‑country entries.
4. Probes each proxy (5s timeout).
5. Prints the survivors, fastest first.

---

### `test_proxy` cheatsheet

| Function | Purpose                                                                          |
|----------|----------------------------------------------------------------------------------|
| `_socks5_handshake` | Sends method‑negotiation (`0x05 0x01 0x00`) and expects `0x05 0x00`.             |
| `_socks4_handshake` | Issues a CONNECT to `1.1.1.1:80`; success if `CD == 0x5A`.                       |
| `_http_probe` | Simple `OPTIONS *` request; success if reply begins with `HTTP/1.`.              |
| `test_proxy` | Wraps the above, records `proxy.ping` on success, leaves it infinity on failure. |

---

## ⚠️ Caveats & Ethics

* Public proxies are unreliable and often abused. Never send sensitive data through them.
* Some endpoints may be compromised or used for MITM. Use TLS end‑to‑end.
* Always respect the target website’s Terms of Service.

---

## 📄 License

This project is released under the **MIT License** – see `LICENSE` for details.