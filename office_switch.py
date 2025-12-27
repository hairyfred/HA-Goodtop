#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoodTop / ZX-AFGW-SWTG218ANS-100 Switch Integration
- PoE control per port
- Status readout (ports, PoE, link, traffic, total PoE power)
"""

import sys, hashlib, requests, re, json, os

BASE = os.environ.get("GOODTOP_HOST", "http://192.168.200.11")
USER = os.environ.get("GOODTOP_USER", "admin")
PASS = os.environ.get("GOODTOP_PASS", "")  # Set GOODTOP_PASS environment variable

TIMEOUT = 5  # seconds

def login_session():
    cookie = hashlib.md5(f"{USER}{PASS}".encode()).hexdigest()
    s = requests.Session()
    s.cookies.set("admin", cookie, domain="192.168.200.11", path="/")
    try:
        s.post(
            f"{BASE}/login.cgi",
            data={"username": USER, "password": PASS, "language": "EN", "Response": cookie},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        print(json.dumps({"error": f"Login failed: {e}"}))
        sys.exit(1)
    return s


def set_poe(port, state):
    s = login_session()
    try:
        r = s.post(
            f"{BASE}/pse_port.cgi",
            data={"portid": port, "state": state, "submit": "Apply", "cmd": "poe"},
            timeout=TIMEOUT,
        )
        print(f"PoE port {port} set to {state} (HTTP {r.status_code})")
    except requests.RequestException as e:
        print(json.dumps({"error": f"PoE set failed: {e}"}))
        sys.exit(1)


def get_status():
    s = login_session()
    data = {"ports": []}

    try:
        # ---- Get total PoE system power ----
        r = s.get(f"{BASE}/pse_system.cgi", timeout=TIMEOUT)
        m = re.search(r'name="pse_con_pwr" value="([\d.]+)"', r.text)
        data["poe_total_watts"] = float(m.group(1)) if m else 0.0

        # ---- Get per-port PoE enable/disable (optional) ----
        s.get(f"{BASE}/pse_port.cgi", timeout=TIMEOUT)

        # ---- Get port stats ----
        r = s.get(f"{BASE}/port.cgi?page=stats", timeout=TIMEOUT)
        rows = re.findall(
            r"<tr>\s*<td>(Port\s*\d+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>",
            r.text,
            re.MULTILINE,
        )

        for row in rows:
            portnum = int(re.search(r"\d+", row[0]).group(0))
            data["ports"].append({
                "id": portnum,
                "state": row[1],
                "link": row[2],
                "tx_good": int(row[3]),
                "tx_bad": int(row[4]),
                "rx_good": int(row[5]),
                "rx_bad": int(row[6]),
            })

    except requests.RequestException as e:
        data = {"error": f"Connection error: {e}"}

    return data


if __name__ == "__main__":
    if len(sys.argv) == 3:
        set_poe(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "status":
        result = get_status()
        # Print pure JSON for Home Assistant
        print(json.dumps(result))
    else:
        print("Usage:")
        print("  office_switch.py <port> <0|1>   # toggle PoE")
        print("  office_switch.py status         # show status JSON")
