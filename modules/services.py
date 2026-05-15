"""NestShare — Services module"""
import subprocess

def _run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

SERVICES = {
    "smbd":         {"label": "Samba",        "desc": "Compartilhamento SMB/CIFS",     "icon": "🗂"},
    "nmbd":         {"label": "NetBIOS",       "desc": "Resolução de nomes Windows",    "icon": "📡"},
    "avahi-daemon": {"label": "Avahi",         "desc": "mDNS / Bonjour (descoberta Mac)","icon": "🍎"},
}

def get_service_status(name):
    _, _, rc = _run(f"systemctl is-active {name} 2>/dev/null")
    active = rc == 0
    _, _, rc2 = _run(f"systemctl is-enabled {name} 2>/dev/null")
    enabled = rc2 == 0
    return {"active": active, "enabled": enabled}

def get_all_services():
    result = {}
    for name, meta in SERVICES.items():
        status = get_service_status(name)
        result[name] = {**meta, **status}
    return result

def start_service(name):
    _, err, rc = _run(f"systemctl start {name}")
    return rc == 0, err

def stop_service(name):
    _, err, rc = _run(f"systemctl stop {name}")
    return rc == 0, err

def restart_service(name):
    _, err, rc = _run(f"systemctl restart {name}")
    return rc == 0, err

def enable_service(name):
    _, err, rc = _run(f"systemctl enable {name}")
    return rc == 0, err

def disable_service(name):
    _, err, rc = _run(f"systemctl disable {name}")
    return rc == 0, err

def get_service_logs(name, lines=50):
    out, _, _ = _run(f"journalctl -u {name} -n {lines} --no-pager 2>/dev/null")
    return out

def check_installed(cmd):
    import shutil
    return shutil.which(cmd) is not None
