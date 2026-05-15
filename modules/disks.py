"""NestShare — Disks module"""
import json, subprocess, os

def _run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def get_disks():
    out, _, rc = _run("lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINT,LABEL,FSTYPE,UUID,HOTPLUG,RM 2>/dev/null")
    disks = []
    if rc != 0:
        return disks
    try:
        data = json.loads(out)
        for dev in data.get("blockdevices", []):
            if dev.get("type") == "disk":
                for part in (dev.get("children") or []):
                    if part.get("type") == "part":
                        disks.append({
                            "device":     f"/dev/{part['name']}",
                            "label":      part.get("label") or part["name"],
                            "size":       part.get("size", "?"),
                            "fstype":     part.get("fstype") or "desconhecido",
                            "mountpoint": part.get("mountpoint") or "",
                            "uuid":       part.get("uuid") or "",
                            "removable":  part.get("rm") == "1" or part.get("hotplug") == "1",
                        })
    except Exception:
        pass
    return disks

def get_disk_usage(mountpoint):
    if not mountpoint or not os.path.exists(mountpoint):
        return None
    try:
        st = os.statvfs(mountpoint)
        total = st.f_blocks * st.f_frsize
        free  = st.f_bfree  * st.f_frsize
        used  = total - free
        pct   = round(used / total * 100) if total > 0 else 0
        def hr(b):
            for u in ["B","KB","MB","GB","TB"]:
                if b < 1024: return f"{b:.1f} {u}"
                b /= 1024
            return f"{b:.1f} PB"
        return {"total": hr(total), "used": hr(used), "free": hr(free), "pct": pct}
    except Exception:
        return None

def mount_disk(device, mountpoint, fstype="auto"):
    os.makedirs(mountpoint, exist_ok=True)
    _, err, rc = _run(f"mount -t {fstype} {device} {mountpoint}")
    return rc == 0, err

def umount_disk(mountpoint):
    _, err, rc = _run(f"umount {mountpoint}")
    return rc == 0, err

def add_fstab(device, mountpoint, fstype="auto", options="defaults,nofail"):
    line = f"{device}  {mountpoint}  {fstype}  {options}  0  2\n"
    try:
        with open("/etc/fstab") as f:
            content = f.read()
        if device in content:
            return False, "Entrada já existe no fstab"
        with open("/etc/fstab", "a") as f:
            f.write(line)
        return True, ""
    except Exception as e:
        return False, str(e)
