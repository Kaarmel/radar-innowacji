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
# Harmonogram aktualizacji źródeł (ten sam co w radar/slowniki.py: HARMONOGRAM i na stronie /warunki)
chmod +x /home/eouser/radar/wdrozenie/aktualizuj.sh
sudo tee /etc/systemd/system/radar-aktualizacja@.service > /dev/null <<'EOF'
[Unit]
Description=Radar Innowacji: aktualizacja źródła %i
After=network-online.target

[Service]
Type=oneshot
User=eouser
Nice=10
ExecStart=/home/eouser/radar/wdrozenie/aktualizuj.sh %i
EOF
for wpis in "mapadotacji|Mon *-*-* 03:00 Europe/Warsaw" "radon|Tue *-*-* 03:00 Europe/Warsaw" "radon_patenty|Wed *-*-* 03:00 Europe/Warsaw" "uprp|Thu *-*-* 03:00 Europe/Warsaw" "interreg|*-*-01 03:30 Europe/Warsaw" "radar|*-*-* *:05:00 Europe/Warsaw"; do
  zr="${wpis%%|*}"; kiedy="${wpis#*|}"
  sudo tee /etc/systemd/system/radar-aktualizacja-$zr.timer > /dev/null <<EOF
[Unit]
Description=Radar Innowacji: harmonogram $zr

[Timer]
OnCalendar=$kiedy
Persistent=true
Unit=radar-aktualizacja@$zr.service

[Install]
WantedBy=timers.target
EOF
  sudo systemctl enable radar-aktualizacja-$zr.timer
done
sudo systemctl daemon-reload
for zr in mapadotacji radon radon_patenty uprp interreg radar; do sudo systemctl start radar-aktualizacja-$zr.timer; done
sudo systemctl restart radar-aktualizacja-radar.timer   # nowy harmonogram radaru (co godzinę) działa od razu
sudo systemctl enable --now radar-innowacji
sudo systemctl restart radar-innowacji
command -v pdftotext > /dev/null || sudo apt-get install -y -q poppler-utils > /dev/null   # Biuletyn UPRP (PDF)
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1
sudo systemctl reload caddy
sleep 3
systemctl is-active radar-innowacji
curl -s -o /dev/null -w "lokalnie %{http_code}\n" http://127.0.0.1:8090/
