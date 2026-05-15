#!/usr/bin/env python3
"""
NestShare — Dashboard de rede para Linux
Compartilhamentos SMB, Time Machine, usuários e serviços.
"""

import os, json, tempfile, secrets
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from modules import network, disks, users, services, shares
from modules.auth import authenticate

app = Flask(__name__)

_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret_key")
if os.path.exists(_KEY_FILE):
    with open(_KEY_FILE) as _f:
        app.secret_key = _f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(_KEY_FILE, "w") as _f:
        _f.write(app.secret_key)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "unauthorized"}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated

# ── Auth ───────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username and authenticate(username, password):
            session["user"] = username
            return redirect(request.args.get("next") or url_for("index"))
        error = "Usuário ou senha incorretos."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Pages ──────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html",
        hostname   = network.get_hostname(),
        primary_ip = network.get_primary_ip(),
        ifaces     = network.get_interfaces(),
        all_disks  = disks.get_disks(),
        all_services = services.get_all_services(),
        all_shares = shares.parse_shares(),
        samba_users = users.get_samba_users(),
        samba_ok   = services.check_installed("smbd"),
        avahi_ok   = services.check_installed("avahi-daemon"),
        current_user = session.get("user"),
    )

# ── API: Status ────────────────────────────────────────────────────────────────

@app.route("/api/status")
@login_required
def api_status():
    all_disks = disks.get_disks()
    for d in all_disks:
        if d["mountpoint"]:
            d["usage"] = disks.get_disk_usage(d["mountpoint"])
    return jsonify({
        "hostname":  network.get_hostname(),
        "ifaces":    network.get_interfaces(),
        "disks":     all_disks,
        "services":  services.get_all_services(),
        "shares":    shares.parse_shares(),
        "users":     users.get_samba_users(),
    })

# ── API: Services ──────────────────────────────────────────────────────────────

@app.route("/api/services/<name>/<action>", methods=["POST"])
@login_required
def api_service_action(name, action):
    allowed = {"start", "stop", "restart", "enable", "disable"}
    if action not in allowed:
        return jsonify({"ok": False, "error": "Ação inválida"}), 400
    fn = getattr(services, f"{action}_service")
    ok, err = fn(name)
    return jsonify({"ok": ok, "error": err})

@app.route("/api/services/<name>/logs")
@login_required
def api_service_logs(name):
    lines = int(request.args.get("lines", 60))
    log = services.get_service_logs(name, lines)
    return jsonify({"ok": True, "log": log})

# ── API: Disks ─────────────────────────────────────────────────────────────────

@app.route("/api/disks")
@login_required
def api_disks():
    all_disks = disks.get_disks()
    for d in all_disks:
        if d["mountpoint"]:
            d["usage"] = disks.get_disk_usage(d["mountpoint"])
    return jsonify({"ok": True, "disks": all_disks})

@app.route("/api/disks/mount", methods=["POST"])
@login_required
def api_mount():
    data = request.get_json(force=True)
    ok, err = disks.mount_disk(data["device"], data["mountpoint"], data.get("fstype","auto"))
    return jsonify({"ok": ok, "error": err})

@app.route("/api/disks/umount", methods=["POST"])
@login_required
def api_umount():
    data = request.get_json(force=True)
    ok, err = disks.umount_disk(data["mountpoint"])
    return jsonify({"ok": ok, "error": err})

@app.route("/api/disks/fstab", methods=["POST"])
@login_required
def api_fstab():
    data = request.get_json(force=True)
    ok, err = disks.add_fstab(data["device"], data["mountpoint"], data.get("fstype","auto"))
    return jsonify({"ok": ok, "error": err})

# ── API: Shares ────────────────────────────────────────────────────────────────

@app.route("/api/shares", methods=["GET"])
@login_required
def api_shares_list():
    return jsonify({"ok": True, "shares": shares.parse_shares()})

@app.route("/api/shares", methods=["POST"])
@login_required
def api_shares_add():
    cfg = request.get_json(force=True)
    errors = []
    if not cfg.get("name"):      errors.append("Nome do share obrigatório.")
    if not cfg.get("path"):      errors.append("Caminho obrigatório.")
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    workgroup = cfg.pop("workgroup", "WORKGROUP")
    ok, err = shares.add_share(cfg, workgroup)
    return jsonify({"ok": ok, "error": err})

@app.route("/api/shares/<name>", methods=["DELETE"])
@login_required
def api_shares_delete(name):
    ok, err = shares.remove_share(name)
    return jsonify({"ok": ok, "error": err})

@app.route("/api/shares/preview", methods=["POST"])
@login_required
def api_shares_preview():
    data = request.get_json(force=True)
    share_list = data.get("shares", [])
    workgroup  = data.get("workgroup", "WORKGROUP")
    conf = shares.build_smb_conf(share_list, workgroup)
    return jsonify({"ok": True, "conf": conf})

@app.route("/api/shares/script", methods=["POST"])
@login_required
def api_shares_script():
    data = request.get_json(force=True)
    share_list = data.get("shares", [])
    user_list  = data.get("users", [])
    workgroup  = data.get("workgroup", "WORKGROUP")
    script = shares.generate_setup_script(share_list, user_list, workgroup)
    return jsonify({"ok": True, "script": script})

@app.route("/api/shares/download_script", methods=["POST"])
@login_required
def api_download_script():
    data = request.get_json(force=True)
    script = shares.generate_setup_script(
        data.get("shares", []),
        data.get("users", []),
        data.get("workgroup", "WORKGROUP"),
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sh", mode="w")
    tmp.write(script); tmp.close()
    return send_file(tmp.name, as_attachment=True,
                     download_name="setup_nestsshare.sh",
                     mimetype="text/x-shellscript")

# ── API: Users ─────────────────────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@login_required
def api_users_list():
    return jsonify({"ok": True, "users": users.get_samba_users()})

@app.route("/api/users", methods=["POST"])
@login_required
def api_users_create():
    data = request.get_json(force=True)
    if not data.get("name"): return jsonify({"ok": False, "error": "Nome obrigatório"}), 400
    ok, err = users.create_user(data["name"], data.get("password",""))
    return jsonify({"ok": ok, "error": err})

@app.route("/api/users/<name>", methods=["DELETE"])
@login_required
def api_users_delete(name):
    ok, err = users.delete_user(name)
    return jsonify({"ok": ok, "error": err})

@app.route("/api/users/<name>/password", methods=["POST"])
@login_required
def api_users_password(name):
    data = request.get_json(force=True)
    ok, err = users.set_password(name, data.get("password",""))
    return jsonify({"ok": ok, "error": err})

@app.route("/api/users/<name>/enable", methods=["POST"])
@login_required
def api_users_enable(name):
    ok, err = users.enable_user(name)
    return jsonify({"ok": ok, "error": err})

@app.route("/api/users/<name>/disable", methods=["POST"])
@login_required
def api_users_disable(name):
    ok, err = users.disable_user(name)
    return jsonify({"ok": ok, "error": err})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
