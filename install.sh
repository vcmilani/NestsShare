#!/usr/bin/env bash
# ============================================================
#  NestShare — Instalação
# ============================================================
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || error "Execute como root: sudo bash install.sh"

INSTALL_DIR="/opt/nestsshare"
PORT=5000

info "Instalando Python3 e dependências do sistema..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv libpam0g-dev

info "Copiando arquivos para $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r . "$INSTALL_DIR/"

info "Criando ambiente virtual e instalando dependências..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

info "Instalando serviço systemd..."
cp nestsshare.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable nestsshare
systemctl start nestsshare

IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✓ NestShare instalado!${NC}"
echo ""
echo "  Acesse: http://${IP}:${PORT}"
echo ""
echo "  sudo systemctl status nestsshare"
echo "  sudo journalctl -u nestsshare -f"
