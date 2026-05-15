"""NestShare — Samba Users module"""
import subprocess, re

def _run(cmd, input_data=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=input_data)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def get_samba_users():
    out, _, rc = _run("pdbedit -L 2>/dev/null")
    users = []
    if rc != 0:
        return users
    for line in out.splitlines():
        parts = line.split(":")
        if parts:
            name = parts[0].strip()
            if name:
                users.append({"name": name, "uid": parts[1].strip() if len(parts) > 1 else ""})
    return users

def create_user(username, password):
    # Create system user (no login shell)
    _, err1, rc1 = _run(f"id {username} 2>/dev/null || useradd -M -s /sbin/nologin {username}")
    # Add to Samba
    _, err2, rc2 = _run(f"smbpasswd -s -a {username}", input_data=f"{password}\n{password}\n")
    ok = rc2 == 0
    return ok, (err1 + err2).strip()

def set_password(username, password):
    _, err, rc = _run(f"smbpasswd -s {username}", input_data=f"{password}\n{password}\n")
    return rc == 0, err

def delete_user(username):
    _, err, rc = _run(f"smbpasswd -x {username}")
    return rc == 0, err

def enable_user(username):
    _, err, rc = _run(f"smbpasswd -e {username}")
    return rc == 0, err

def disable_user(username):
    _, err, rc = _run(f"smbpasswd -d {username}")
    return rc == 0, err
