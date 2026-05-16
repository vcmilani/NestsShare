#!/usr/bin/env bash
# ============================================================
#  NestShare — Atualização
# ============================================================
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || error "Execute como root: sudo bash update.sh"

INSTALL_DIR="/opt/nestshare"
SERVICE="nestshare"
PORT=5000

[ -d "$INSTALL_DIR" ] || error "NestShare não está instalado em $INSTALL_DIR. Use install.sh primeiro."

info "Parando serviço..."
systemctl stop "$SERVICE" 2>/dev/null || warn "Serviço não estava rodando."

info "Fazendo backup de arquivos sensíveis..."
BACKUP_DIR=$(mktemp -d /tmp/nestshare_bak.XXXXXX)
[ -f "$INSTALL_DIR/.secret_key" ] && cp "$INSTALL_DIR/.secret_key" "$BACKUP_DIR/"
[ -f "$INSTALL_DIR/cert.pem"    ] && cp "$INSTALL_DIR/cert.pem"    "$BACKUP_DIR/"
[ -f "$INSTALL_DIR/key.pem"     ] && cp "$INSTALL_DIR/key.pem"     "$BACKUP_DIR/"

info "Copiando novos arquivos para $INSTALL_DIR..."
# Copia tudo exceto os arquivos sensíveis que já foram preservados
rsync -a --exclude='.secret_key' \
         --exclude='cert.pem' \
         --exclude='key.pem' \
         --exclude='venv/' \
         --exclude='__pycache__/' \
         --exclude='*.pyc' \
         . "$INSTALL_DIR/"

info "Restaurando arquivos sensíveis..."
[ -f "$BACKUP_DIR/.secret_key" ] && cp "$BACKUP_DIR/.secret_key" "$INSTALL_DIR/"
[ -f "$BACKUP_DIR/cert.pem"    ] && cp "$BACKUP_DIR/cert.pem"    "$INSTALL_DIR/"
[ -f "$BACKUP_DIR/key.pem"     ] && cp "$BACKUP_DIR/key.pem"     "$INSTALL_DIR/"
rm -rf "$BACKUP_DIR"

info "Atualizando dependências Python..."
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade -r "$INSTALL_DIR/requirements.txt"

info "Atualizando serviço systemd..."
cp nestshare.service /etc/systemd/system/
systemctl daemon-reload

info "Reiniciando serviço..."
systemctl start "$SERVICE"

IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✓ NestShare atualizado com sucesso!${NC}"
echo ""
echo "  Acesse: https://${IP}:${PORT}"
echo ""
echo "  sudo systemctl status nestshare"
echo "  sudo journalctl -u nestshare -f"
