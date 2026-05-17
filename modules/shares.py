"""NestShare — SMB Shares module"""
import subprocess, os, re, configparser, io, shlex

SMB_CONF     = "/etc/samba/smb.conf"
AVAHI_SERVICE = "/etc/avahi/services/samba.service"

def _run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

# ── Read current shares ────────────────────────────────────────────────────────

def parse_shares():
    """Parse smb.conf and return list of share dicts (excluding [global])."""
    if not os.path.exists(SMB_CONF):
        return []
    cfg = configparser.RawConfigParser(strict=False)
    cfg.read(SMB_CONF)
    shares = []
    for section in cfg.sections():
        if section.lower() == "global":
            continue
        s = dict(cfg.items(section))
        shares.append({
            "name":         section,
            "path":         s.get("path", ""),
            "comment":      s.get("comment", ""),
            "browseable":   s.get("browseable", "yes"),
            "writeable":    s.get("writeable", s.get("writable", "yes")),
            "valid_users":  s.get("valid users", ""),
            "time_machine": s.get("fruit:time machine", "no").lower() == "yes",
        })
    return shares

def get_global_conf():
    if not os.path.exists(SMB_CONF):
        return {}
    cfg = configparser.RawConfigParser(strict=False)
    cfg.read(SMB_CONF)
    if cfg.has_section("global"):
        return dict(cfg.items("global"))
    return {}

# ── Generate configs ───────────────────────────────────────────────────────────

def _global_block(workgroup="WORKGROUP"):
    return f"""[global]
   workgroup = {workgroup}
   server string = NestShare Server
   server role = standalone server
   log file = /var/log/samba/log.%m
   max log size = 50
   dns proxy = no
   multicast dns register = yes
   vfs objects = catia fruit streams_xattr
   fruit:aapl = yes
   fruit:nfs_aces = no
   fruit:copyfile = no
   fruit:model = MacSamba
   fruit:metadata = stream
   streams_xattr:prefix = user.
   streams_xattr:store_stream_type = no

"""

def _share_block(cfg):
    name        = cfg["name"]
    path        = cfg["path"]
    comment     = cfg.get("comment", "")
    writeable   = "yes" if cfg.get("writeable", True) else "no"
    browseable  = "yes" if cfg.get("browseable", True) else "no"
    valid_users = cfg.get("valid_users", "")
    time_machine = cfg.get("time_machine", False)
    max_size_gb  = cfg.get("max_size_gb", 0)
    readonly    = cfg.get("readonly", False)

    block = f"[{name}]\n"
    if comment:
        block += f"   comment = {comment}\n"
    block += f"   path = {path}\n"
    block += f"   browseable = {browseable}\n"
    block += f"   writeable = {'no' if readonly else writeable}\n"
    block += f"   create mask = 0664\n"
    block += f"   directory mask = 0775\n"
    if valid_users:
        block += f"   valid users = {valid_users}\n"
    if time_machine:
        block += f"   vfs objects = catia fruit streams_xattr\n"
        block += f"   fruit:aapl = yes\n"
        block += f"   fruit:time machine = yes\n"
        if max_size_gb:
            block += f"   fruit:time machine max size = {max_size_gb}G\n"
        if valid_users:
            first_user = re.split(r"[,\s]+", valid_users.strip())[0]
            block += f"   force user = {first_user}\n"
    block += "\n"
    return block

def build_smb_conf(shares, workgroup="WORKGROUP"):
    """Build full smb.conf from list of share dicts."""
    conf = _global_block(workgroup)
    for share in shares:
        conf += _share_block(share)
    return conf

def write_smb_conf(conf_text):
    """Backup and write new smb.conf."""
    import shutil, time
    if os.path.exists(SMB_CONF):
        shutil.copy(SMB_CONF, SMB_CONF + f".bak.{int(time.time())}")
    try:
        with open(SMB_CONF, "w") as f:
            f.write(conf_text)
        return True, ""
    except Exception as e:
        return False, str(e)

def validate_smb_conf():
    out, err, rc = _run("testparm -s 2>&1")
    return rc == 0, (out + err).strip()

def _build_avahi_xml(tm_shares):
    dk_records = "\n".join(
        f'    <txt-record>dk{i}=adVN={s["name"]},adVF=0x82</txt-record>'
        for i, s in enumerate(tm_shares)
    )
    return f"""<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_smb._tcp</type>
    <port>445</port>
  </service>
  <service>
    <type>_adisk._tcp</type>
    <port>9</port>
    <txt-record>sys=waMa=0,adVF=0x100</txt-record>
{dk_records}
  </service>
</service-group>
"""

def sync_avahi(shares=None):
    """Sync the Avahi _adisk._tcp service file with the current Time Machine shares."""
    if shares is None:
        shares = parse_shares()
    _update_avahi(shares)

def _update_avahi(shares):
    tm_shares = [s for s in shares if s.get("time_machine")]
    if not tm_shares:
        if os.path.exists(AVAHI_SERVICE):
            os.remove(AVAHI_SERVICE)
            _run("systemctl restart avahi-daemon 2>/dev/null || true")
        return
    os.makedirs(os.path.dirname(AVAHI_SERVICE), exist_ok=True)
    with open(AVAHI_SERVICE, "w") as f:
        f.write(_build_avahi_xml(tm_shares))
    _run("systemctl restart avahi-daemon 2>/dev/null || true")

def add_share(share_cfg, workgroup="WORKGROUP"):
    """Add a new share to smb.conf."""
    existing = parse_shares()
    existing = [s for s in existing if s["name"] != share_cfg["name"]]
    existing.append(share_cfg)
    conf = build_smb_conf(existing, workgroup)
    ok, err = write_smb_conf(conf)
    if ok:
        _run("systemctl reload smbd 2>/dev/null || systemctl restart smbd 2>/dev/null")
        _update_avahi(existing)
    return ok, err

def fix_permissions(name):
    """Apply correct filesystem permissions to a share's path based on its config."""
    found = [s for s in parse_shares() if s["name"] == name]
    if not found:
        return False, f"Share '{name}' não encontrado."
    share = found[0]
    path = share.get("path", "").strip()
    if not path:
        return False, "Caminho não definido no share."
    if not os.path.isdir(path):
        return False, f"Diretório não existe: {path}"

    valid_users  = share.get("valid_users", "").strip()
    writeable    = share.get("writeable", "yes") == "yes"
    time_machine = share.get("time_machine", False)
    qpath        = shlex.quote(path)
    cmds         = []

    if valid_users:
        first_user = re.split(r"[,\s]+", valid_users)[0]
        # Time Machine needs exclusive ownership (0700); Samba's force user handles access
        mode = "0700" if time_machine else ("0770" if writeable else "0750")
        cmds = [
            f"chown -R {shlex.quote(first_user)}:{shlex.quote(first_user)} {qpath}",
            f"chmod -R {mode} {qpath}",
        ]
    else:
        mode = "0775" if writeable else "0755"
        cmds = [
            f"chown -R nobody:nogroup {qpath}",
            f"chmod -R {mode} {qpath}",
        ]

    for cmd in cmds:
        _, err, rc = _run(cmd)
        if rc != 0:
            return False, f"Erro ao executar `{cmd}`: {err}"

    return True, "\n".join(cmds)

def remove_share(name, workgroup="WORKGROUP"):
    existing = [s for s in parse_shares() if s["name"] != name]
    conf = build_smb_conf(existing, workgroup)
    ok, err = write_smb_conf(conf)
    if ok:
        _run("systemctl reload smbd 2>/dev/null || systemctl restart smbd 2>/dev/null")
        _update_avahi(existing)
    return ok, err

# ── Setup script generator ─────────────────────────────────────────────────────

def generate_setup_script(shares, users, workgroup="WORKGROUP"):
    smb_conf = build_smb_conf(shares, workgroup)
    smb_conf_esc = smb_conf.replace("'", "'\\''")

    user_cmds = ""
    for u in users:
        uname = u["name"]
        upass = u.get("password", "")
        if upass:
            user_cmds += f"""
if ! id "{uname}" &>/dev/null; then
    useradd -M -s /sbin/nologin "{uname}"
fi
echo '{upass}\\n{upass}' | smbpasswd -s -a "{uname}"
"""
        else:
            user_cmds += f"""
if ! id "{uname}" &>/dev/null; then
    useradd -M -s /sbin/nologin "{uname}"
fi
warn "Usuário '{uname}' criado sem senha — defina com: sudo smbpasswd -a {uname}"
"""

    tm_shares = [s for s in shares if s.get("time_machine")]
    avahi_cmd = ""
    if tm_shares:
        avahi_xml_esc = _build_avahi_xml(tm_shares).replace("'", "'\\''")
        avahi_cmd = f"""
info "Configurando anúncio Bonjour para Time Machine (_adisk._tcp)..."
mkdir -p /etc/avahi/services
cat > /etc/avahi/services/samba.service << 'AVAHICONF'
{avahi_xml_esc}
AVAHICONF
systemctl restart avahi-daemon 2>/dev/null || true
"""

    mount_cmds = ""
    for share in shares:
        if share.get("device") and share.get("path"):
            mount_cmds += f"""
mkdir -p "{share['path']}"
mountpoint -q "{share['path']}" || mount "{share['device']}" "{share['path']}" 2>/dev/null || warn "Falha ao montar {share['device']}"
chown nobody:nogroup "{share['path']}"
chmod 777 "{share['path']}"
"""

    script = f"""#!/usr/bin/env bash
# ============================================================
#  NestShare — Setup Script
#  Gerado automaticamente pelo NestShare Dashboard
# ============================================================
set -euo pipefail
RED='\\033[0;31m'; GREEN='\\033[0;32m'; YELLOW='\\033[1;33m'; NC='\\033[0m'
info()  {{ echo -e "${{GREEN}}[INFO]${{NC}}  $*"; }}
warn()  {{ echo -e "${{YELLOW}}[WARN]${{NC}}  $*"; }}
error() {{ echo -e "${{RED}}[ERR]${{NC}}   $*"; exit 1; }}
[ "$(id -u)" -eq 0 ] || error "Execute como root: sudo bash setup_nestshare.sh"

info "Instalando dependências..."
apt-get update -qq
apt-get install -y samba avahi-daemon

info "Configurando pontos de montagem..."
{mount_cmds}
{avahi_cmd}

info "Escrevendo /etc/samba/smb.conf..."
[ -f /etc/samba/smb.conf ] && cp /etc/samba/smb.conf /etc/samba/smb.conf.bak.$(date +%Y%m%d%H%M%S)
cat > /etc/samba/smb.conf << 'SMBCONF'
{smb_conf_esc}
SMBCONF

info "Configurando usuários Samba..."
{user_cmds}

info "Habilitando e iniciando serviços..."
systemctl enable smbd nmbd avahi-daemon
systemctl restart smbd nmbd avahi-daemon 2>/dev/null || true

if systemctl is-active ufw &>/dev/null; then
    info "UFW detectado — abrindo portas Samba..."
    ufw allow samba
fi

info "Validando configuração..."
testparm -s /etc/samba/smb.conf 2>/dev/null && info "smb.conf OK" || warn "testparm reportou avisos"

echo ""
echo -e "${{GREEN}}✓ NestShare configurado com sucesso!${{NC}}"
echo "  Acesse os compartilhamentos em: smb://$(hostname -I | awk '{{print $1}}')"
"""
    return script
