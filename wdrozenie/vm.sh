#!/usr/bin/env bash
# Wdrożenie na Ubuntu 24.04 (użytkownik eouser): kod z git archive w ~/radar_kod.tgz, baza w ~/radar_kopia.sqlite.gz,
# klucze w ~/.env. Caddy dostaje osobny blok hosta (nie zmienia innych stron na maszynie).
# Przygotowanie lokalnie:
#   git archive --format=tar.gz -o radar_kod.tgz HEAD
#   sqlite3 dane/radar.sqlite ".backup 'radar_kopia.sqlite'" && gzip radar_kopia.sqlite
#   scp radar_kod.tgz radar_kopia.sqlite.gz .env eouser@HOST:~/
set -e
cd ~
mkdir -p radar && tar -xzf radar_kod.tgz -C radar
mv -f .env radar/.env && chmod 600 radar/.env
mkdir -p radar/dane/logi
if [ ! -f radar/dane/radar.sqlite ]; then gunzip -c radar_kopia.sqlite.gz > radar/dane/radar.sqlite; fi
cd radar
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
sudo tee /etc/systemd/system/radar-innowacji.service > /dev/null <<'EOF'
[Unit]
Description=Radar Innowacji (FastAPI, uvicorn)
After=network.target

[Service]
User=eouser
WorkingDirectory=/home/eouser/radar
ExecStart=/home/eouser/radar/.venv/bin/uvicorn radar.app:app --host 127.0.0.1 --port 8090 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
if grep -Fq "radar.46.60.21.253.sslip.io {" /etc/caddy/Caddyfile; then
sudo sed -i 's/^radar\.46\.60\.21\.253\.sslip\.io {/radar-innowacji.skroban.tech, radar.46.60.21.253.sslip.io {/' /etc/caddy/Caddyfile
elif ! grep -Fq "radar-innowacji.skroban.tech" /etc/caddy/Caddyfile; then
sudo tee -a /etc/caddy/Caddyfile > /dev/null <<'EOF'

# Radar Innowacji (HackNation 2026) — osobny host, nie rusza bloku :80
radar-innowacji.skroban.tech, radar.46.60.21.253.sslip.io {
	encode gzip
	reverse_proxy 127.0.0.1:8090
}
EOF
fi
sudo systemctl daemon-reload
sudo systemctl enable --now radar-innowacji
sudo systemctl restart radar-innowacji
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1
sudo systemctl reload caddy
sleep 3
systemctl is-active radar-innowacji
curl -s -o /dev/null -w "lokalnie %{http_code}\n" http://127.0.0.1:8090/
