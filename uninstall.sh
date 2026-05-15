#!/usr/bin/env bash
# ============================================================
#  NestShare — Desinstalação
# ============================================================
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || error "Execute como root: sudo bash uninstall.sh"

INSTALL_DIR="/opt/nestsshare"
SERVICE="nestsshare"

info "Parando e desabilitando serviço..."
systemctl stop "$SERVICE"    2>/dev/null || warn "Serviço não estava rodando."
systemctl disable "$SERVICE" 2>/dev/null || warn "Serviço não estava habilitado."

info "Removendo arquivo de serviço systemd..."
rm -f "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload

info "Removendo arquivos de instalação..."
rm -rf "$INSTALL_DIR"

echo ""
echo -e "${GREEN}✓ NestShare desinstalado com sucesso!${NC}"
echo ""
warn "Os pacotes do sistema (python3, python3-pip, python3-venv, libpam0g-dev)"
warn "não foram removidos pois podem ser usados por outros programas."
warn "Para removê-los manualmente: sudo apt-get remove python3-pip python3-venv libpam0g-dev"
echo ""
