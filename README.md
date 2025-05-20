# ClosestProxy

Find and benchmark **the closest, working public proxy** in seconds.

---

## ✨ Highlights

- **Geolocation-aware**: auto-detects your country (via [ipinfo.io](https://ipinfo.io/)) or lets you specify ISO-3166 codes.
- **Multi-protocol**: probes HTTP, HTTPS, SOCKS4 & SOCKS5 proxies.
- **True latency**: measures handshake _and_ a real HTTPS request.
- **Multiprocess scanning**: uses all CPU cores for speed.
- **Subnet deduplication**: optional CIDR mask to avoid clustered IPs.
- **Zero setup**: grabs the latest proxy list from [proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list) and caches it locally.

---

## 🚀 Quick start

```bash
# 1. Install Python3 dependencies
python3 -m pip install -r requirements.txt

# 2. Run (auto-detects your country)
python3 closestproxy.py

# Specify countries (e.g. US & CA)
python3 closestproxy.py -c US CA

# Deduplicate proxies by /24 subnet
python3 closestproxy.py -c IT FR -s 24
```

The script prints the working proxies sorted by ascending latency, e.g.

```
> Found 312 proxies in {'IT'}
> Found 27 working proxies
> Filtered by netmask=24 -> 12 left
...
```

---

## 🔧 Command-line options

| Flag | Alias | Description |
|------|-------|-------------|
| `--country CC [CC ...]` | `-c` | One or more ISO-3166 country codes. Omit to use your detected country. |
| `--subnet MASK` | `-s` | CIDR mask (0-32) to drop proxies in the same subnet, e.g. `24` for `/24`. |

---

## 🛠 How it works

1. Download or load cached `data.json` (a fresh list of public proxies) in your temp folder.
2. Filter by desired country codes.
3. **Parallel probe** each proxy:
   - Perform protocol-specific handshake (HTTP OPTIONS / SOCKS greeting) to quickly measure latency.
   - Attempt a real request to [https://www.torproject.org/](https://www.torproject.org/) (they should not block proxies).
4. Sort and print only the proxies that responded successfully.

---

## ⚠️ Caveats & ethics

- Public proxies are often unstable; always validate before production use.
- Do **not** use this tool for illegal activities. Respect target sites' ToS.
- Some websites may block known public proxies.

---

## 📄 License

ClosestProxy is released under the MIT License – see `LICENSE` for details.
