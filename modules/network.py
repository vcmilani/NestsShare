"""NestShare — Network module"""
import json, subprocess

def _run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def get_interfaces():
    out, _, rc = _run("ip -j addr show 2>/dev/null")
    ifaces = []
    if rc != 0:
        return ifaces
    try:
        for iface in json.loads(out):
            name = iface.get("ifname", "")
            if name == "lo":
                continue
            state = iface.get("operstate", "UNKNOWN").lower()
            addrs = [a.get("local","") for a in iface.get("addr_info",[]) if a.get("family")=="inet"]
            ifaces.append({"name": name, "state": state, "ips": addrs})
    except Exception:
        pass
    return ifaces

def get_hostname():
    out, _, _ = _run("hostname")
    return out

def get_primary_ip():
    ifaces = get_interfaces()
    for iface in ifaces:
        if iface["ips"]:
            return iface["ips"][0]
    return "127.0.0.1"
