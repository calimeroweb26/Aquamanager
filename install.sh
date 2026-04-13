cat > /usr/local/bin/aquamanager-install.sh << 'EOF'
#!/usr/bin/env bash

# ============================================
#  AquaManager - Proxmox LXC Install Script
#  Auteur : calimeroweb26
#  Github : https://github.com/calimeroweb26/AquaManager
# ============================================

set -e

# Couleurs
YW=$(echo "\033[33m")
GN=$(echo "\033[1;92m")
RD=$(echo "\033[01;31m")
CL=$(echo "\033[m")
BL=$(echo "\033[36m")
CM="${GN}✓${CL}"
CROSS="${RD}✗${CL}"
INFO="${BL}ℹ${CL}"

header_info() {
  clear
  cat << "BANNER"
    ___                   __  ___                                   
   /   | ____ ___  ____  /  |/  /___ _____  ____ _____ ____  _____ 
  / /| |/ __ `/ / / / / / /|_/ / __ `/ __ \/ __ `/ __ `/ _ \/ ___/ 
 / ___ / /_/ / /_/ / / / /  / / /_/ / / / / /_/ / /_/ /  __/ /     
/_/  |_\__, /\__,_/_/ /_/  /_/\__,_/_/ /_/\__,_/\__, /\___/_/      
         /_/                                     /____/              
BANNER
  echo -e "${GN}  Proxmox LXC Auto-Installer${CL}"
  echo -e "${BL}  https://github.com/calimeroweb26/AquaManager${CL}"
  echo ""
}

# ---- Variables ----
GITHUB_USER="calimeroweb26"
GITHUB_REPO="AquaManager"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/main"
CT_NAME="AquaManager"
CT_RAM="512"
CT_DISK="4"
CT_CPU="1"
CT_OS="debian"
CT_OS_VERSION="12"
TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"
TEMPLATE_STORAGE="local"
CT_STORAGE="local-lvm"
BRIDGE="vmbr0"
APP_PORT="80"

header_info

# ---- Vérification Proxmox ----
if ! command -v pveversion &>/dev/null; then
  echo -e "${CROSS} Ce script doit être lancé sur un hôte Proxmox VE"
  exit 1
fi

echo -e "${INFO} Proxmox détecté : $(pveversion)"
echo ""

# ---- Choix utilisateur ----
read -p "  RAM en MB [512] : " INPUT_RAM
CT_RAM="${INPUT_RAM:-512}"

read -p "  Disk en GB [4] : " INPUT_DISK
CT_DISK="${INPUT_DISK:-4}"

read -p "  CPU cores [1] : " INPUT_CPU
CT_CPU="${INPUT_CPU:-1}"

echo ""

# ---- ID automatique ----
CT_ID=$(pvesh get /cluster/nextid)
echo -e "${CM} ID LXC attribué automatiquement : ${GN}${CT_ID}${CL}"

# ---- IP via DHCP ----
echo -e "${CM} Réseau : ${GN}DHCP${CL} sur ${BRIDGE}"

# ---- Téléchargement du template ----
echo ""
echo -e "${INFO} Vérification du template ${TEMPLATE}..."

if ! pveam list ${TEMPLATE_STORAGE} | grep -q "${TEMPLATE}"; then
  echo -e "${INFO} Téléchargement du template Debian 12..."
  pveam update
  pveam download ${TEMPLATE_STORAGE} ${TEMPLATE}
  echo -e "${CM} Template téléchargé"
else
  echo -e "${CM} Template déjà présent"
fi

# ---- Création du LXC ----
echo ""
echo -e "${INFO} Création du conteneur LXC ${CT_ID}..."

pct create ${CT_ID} ${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE} \
  --hostname ${CT_NAME} \
  --memory ${CT_RAM} \
  --cores ${CT_CPU} \
  --rootfs ${CT_STORAGE}:${CT_DISK} \
  --net0 name=eth0,bridge=${BRIDGE},ip=dhcp \
  --ostype ${CT_OS} \
  --unprivileged 1 \
  --features nesting=1 \
  --start 1 \
  --onboot 1

echo -e "${CM} LXC ${CT_ID} créé et démarré"

# ---- Attente démarrage + IP DHCP ----
echo ""
echo -e "${INFO} Attente de l'IP DHCP..."
sleep 8

CT_IP=""
ATTEMPTS=0
while [ -z "$CT_IP" ] && [ $ATTEMPTS -lt 15 ]; do
  CT_IP=$(pct exec ${CT_ID} -- hostname -I 2>/dev/null | awk '{print $1}')
  ATTEMPTS=$((ATTEMPTS + 1))
  [ -z "$CT_IP" ] && sleep 3
done

if [ -z "$CT_IP" ]; then
  echo -e "${CROSS} Impossible d'obtenir une IP, vérifiez le DHCP"
  CT_IP="inconnue"
else
  echo -e "${CM} IP obtenue : ${GN}${CT_IP}${CL}"
fi

# ---- Installation dans le LXC ----
echo ""
echo -e "${INFO} Installation des dépendances dans le LXC..."

pct exec ${CT_ID} -- bash -c "
  apt-get update -qq
  apt-get upgrade -y -qq
  apt-get install -y curl wget git nginx sqlite3 ca-certificates gnupg
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
  echo 'Dépendances OK'
"

echo -e "${CM} Dépendances installées"

# ---- Récupération des fichiers GitHub ----
echo ""
echo -e "${INFO} Récupération des fichiers depuis GitHub..."

pct exec ${CT_ID} -- bash -c "
  mkdir -p /opt/aquamanager/{data,uploads}
  cd /opt/aquamanager
  git clone https://github.com/${GITHUB_USER}/${GITHUB_REPO}.git /tmp/aquarepo
  cp -r /tmp/aquarepo/backend  /opt/aquamanager/ 2>/dev/null || echo 'Pas de dossier backend'
  cp -r /tmp/aquarepo/frontend /opt/aquamanager/ 2>/dev/null || echo 'Pas de dossier frontend'
  rm -rf /tmp/aquarepo
  chmod 755 /opt/aquamanager/uploads
  echo 'Fichiers GitHub OK'
"

echo -e "${CM} Fichiers récupérés depuis GitHub"

# ---- NPM Install ----
echo ""
echo -e "${INFO} Installation des modules Node.js..."

pct exec ${CT_ID} -- bash -c "
  cd /opt/aquamanager/backend
  npm install --silent
  echo 'NPM OK'
"

echo -e "${CM} Modules Node.js installés"

# ---- Service Systemd ----
echo ""
echo -e "${INFO} Configuration du service systemd..."

pct exec ${CT_ID} -- bash -c "
cat > /etc/systemd/system/aquamanager.service << 'SVCEOF'
[Unit]
Description=AquaManager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aquamanager/backend
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
SVCEOF
systemctl daemon-reload
systemctl enable aquamanager
systemctl start aquamanager
echo 'Service OK'
"

echo -e "${CM} Service systemd configuré"

# ---- Nginx ----
echo ""
echo -e "${INFO} Configuration Nginx..."

pct exec ${CT_ID} -- bash -c "
cat > /etc/nginx/sites-available/aquamanager << 'NGEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
NGEOF
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/aquamanager /etc/nginx/sites-enabled/aquamanager
nginx -t && systemctl restart nginx
echo 'Nginx OK'
"

echo -e "${CM} Nginx configuré"

# ---- Résumé final ----
echo ""
echo -e "${GN}============================================${CL}"
echo -e "${GN}   AquaManager installé avec succès !${CL}"
echo -e "${GN}============================================${CL}"
echo -e "  ${INFO} LXC ID     : ${GN}${CT_ID}${CL}"
echo -e "  ${INFO} Nom        : ${GN}${CT_NAME}${CL}"
echo -e "  ${INFO} IP         : ${GN}${CT_IP}${CL}"
echo -e "  ${INFO} RAM        : ${GN}${CT_RAM} MB${CL}"
echo -e "  ${INFO} CPU        : ${GN}${CT_CPU} core(s)${CL}"
echo -e "  ${INFO} Disk       : ${GN}${CT_DISK} GB${CL}"
echo -e "  ${INFO} Accès      : ${GN}http://${CT_IP}${CL}"
echo -e "${GN}============================================${CL}"
echo ""

EOF

chmod +x /usr/local/bin/aquamanager-install.sh
echo "Script créé ! Lancez-le avec :"
echo "bash /usr/local/bin/aquamanager-install.sh"
