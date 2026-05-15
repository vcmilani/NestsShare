# 🪺 NestShare

Dashboard web para gerenciar compartilhamentos SMB, Time Machine, usuários e serviços em Linux (Raspberry Pi, PC antigo, servidor).

Irmão do **NestVault** — mesmo ecossistema, foco em compartilhamento de rede.

> ⚠️ **Exclusivo para Linux.** O NestShare depende de ferramentas nativas do Linux (`lsblk`, `ip`, `systemctl`, `smbpasswd`, `pdbedit`) e não funciona em macOS ou Windows. O dashboard em si pode ser acessado de qualquer navegador na rede local, mas o servidor deve rodar em Linux.

## Compatibilidade de distros

| Distro | Versão | Suporte | Observação |
|--------|--------|---------|------------|
| **Ubuntu Server** | 22.04 / 24.04 LTS | ✅ Garantido | Alvo principal do projeto |
| **Debian** | 11 / 12 | ✅ Garantido | Mesma base, comportamento idêntico |
| **Raspberry Pi OS** | 64-bit (Bookworm) | ✅ Garantido | Testado com Samba, base Debian |
| **Linux Mint** | 21+ | 🟡 Provável | Base Ubuntu, deve funcionar |
| **Pop!_OS** | 22.04+ | 🟡 Provável | Base Ubuntu, deve funcionar |
| **Armbian** | atual | 🟡 Provável | Comum em SBCs, base Debian |
| **Fedora / RHEL** | qualquer | ❌ Não suportado | Usa `dnf` e `firewalld`; requer adaptação |
| **Arch / Manjaro** | qualquer | ❌ Não suportado | Usa `pacman`; nomes de pacotes e serviços diferem |
| **openSUSE** | qualquer | ❌ Não suportado | Usa `zypper`; estrutura diferente |
| **Alpine Linux** | qualquer | ❌ Não suportado | Sem systemd (usa OpenRC) |

**Regra geral:** qualquer distro baseada em **Debian/Ubuntu com systemd** deve funcionar. O script de instalação usa `apt-get` e assume `systemctl` disponível.

## Funcionalidades

- **Compartilhamentos SMB** — criar, listar e remover shares; suporte a Time Machine, somente leitura e geral
- **Time Machine** — opção dedicada com configuração automática do `vfs fruit`
- **Usuários Samba** — criar, alterar senha, remover usuários
- **Discos** — listar, montar, desmontar, adicionar ao fstab
- **Serviços** — controle de smbd, nmbd, avahi-daemon com logs em tempo real
- **Setup / Script** — gera `smb.conf` e script bash completo para instalação

## Instalação rápida

```bash
# Transferir para o servidor
scp -r nestshare/ usuario@<IP>:~/

# No servidor
cd nestshare
sudo bash install.sh

# Acessar (aceite o aviso de certificado auto-assinado no browser)
https://<IP>:5000
```

## Uso manual

```bash
pip3 install flask
sudo python3 app.py
```

## Estrutura

```
nestshare/
├── app.py                  # Flask — rotas e API REST
├── modules/
│   ├── network.py          # Interfaces e IPs
│   ├── disks.py            # Volumes, montagem, fstab
│   ├── users.py            # Usuários Samba
│   ├── services.py         # Controle de serviços systemd
│   └── shares.py           # SMB shares, smb.conf, scripts
├── templates/
│   ├── index.html          # Dashboard completo
│   └── login.html          # Tela de login
├── requirements.txt
├── nestshare.service       # Systemd unit
├── install.sh              # Instalação (gera certificado SSL)
├── uninstall.sh            # Remoção completa
└── release.sh              # Gera ZIP para distribuição
```

## API REST

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/status` | Status geral |
| GET/POST | `/api/shares` | Listar / criar share |
| DELETE | `/api/shares/<name>` | Remover share |
| POST | `/api/shares/preview` | Gerar smb.conf |
| POST | `/api/shares/script` | Gerar script bash |
| GET/POST | `/api/users` | Listar / criar usuário |
| DELETE | `/api/users/<name>` | Remover usuário |
| POST | `/api/users/<name>/password` | Alterar senha |
| POST | `/api/services/<name>/<action>` | start/stop/restart/enable/disable |
| GET | `/api/services/<name>/logs` | Logs do serviço |
| POST | `/api/disks/mount` | Montar disco |
| POST | `/api/disks/umount` | Desmontar |
| POST | `/api/disks/fstab` | Adicionar ao fstab |

## Família Nest

- **NestVault** — sistema de backup local
- **NestShare** — compartilhamento de rede e Time Machine
