# Raspberry Pi 3B Watchdog — Setup Guide

## What This Does
- Watches your Proxmox VMs (`lux-runner-linux`, `lux-runner-windows`)
- Checks status every 30 seconds
- Streams real-time status to log
- Alerts via Hermes when VMs change state

---

## Prerequisites

1. **Raspberry Pi 3B** with microSD card (16GB+)
2. **Raspberry Pi OS Lite (64-bit)** installed via [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
3. **Network connection** (Ethernet recommended)
4. **Proxmox server** at `pve.starbounded.com` (root/nivaniva)

---

## Step 1: Flash the SD Card

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert SD card
3. Open Imager → Choose OS → **Raspberry Pi OS Lite (64-bit)**
4. Choose Storage → your SD card
5. Click **Next** → Configure settings:
   - Hostname: `pi3b`
   - Username: `pi`
   - Password: (your choice)
   - Wireless LAN: Your Wi-Fi
   - SSH: Enable → Use password authentication
   - Advanced options: Set `wpa-ssid` and `wpa-psk`
6. Click **Write**

---

## Step 2: Boot & Find IP

1. Insert SD card into Pi
2. Connect to network (Ethernet recommended)
3. Power up
4. Find IP:
   ```bash
   ping pi3b.local
   ```
   Or check your router's DHCP list.

---

## Step 3: Log into the Pi

```bash
ssh pi@pi3b.local
```

Change password on first login:
```bash
passwd
```

---

## Step 4: Update & Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git curl
```

---

## Step 5: Set Up SSH Keys to Proxmox

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "pi3b-watchdog"
ssh-copy-id root@pve.starbounded.com
```

You'll be prompted for your Proxmox password once. After that, you can SSH to Proxmox without a password.

---

## Step 6: Download the Watchdog Script

```bash
cd ~
wget https://raw.githubusercontent.com/yourusername/watchdog/main/watchdog.py
chmod +x watchdog.py
```

---

## Step 7: Test It

```bash
python3 watchdog.py \
  --host pve.starbounded.com \
  --user root \
  --password nivaniva \
  --vm-names lux-runner-linux,lux-runner-windows \
  --interval 30
```

Wait 60–90 seconds, press `Ctrl+C`.

Check log:
```bash
cat watchdog.log
```

Expected output:
```
[INFO] Starting Pi Watchdog...
[PASS] Linux: lux-runner-linux is running
[PASS] Windows: lux-runner-windows is running
```

---

## Step 8: Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/pi-watchdog.service
```

Paste this (replace values if needed):

```ini
[Unit]
Description=Pi CI Watchdog
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /home/pi/watchdog.py --host pve.starbounded.com --user root --password nivaniva --vm-names lux-runner-linux,lux-runner-windows --interval 30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-watchdog
sudo systemctl start pi-watchdog
sudo systemctl status pi-watchdog
```

Watch logs:
```bash
journalctl -u pi-watchdog -f
```

---

## Troubleshooting

### Script won't start
```bash
sudo journalctl -u pi-watchdog -f
```

### Can't connect to Proxmox
```bash
ssh root@pve.starbounded.com
```

### VMs not showing as running
- Check VM names in Proxmox Web UI
- VM names are case-sensitive

### Alerts not sending
- The `@hermes` alert is a placeholder — you'll need to implement the actual message_agent call
- Check the `send_alert_to_hermes()` function in `watchdog.py`

---

## What You'll See

When working, the Pi shows:
```
[INFO] Starting Pi Watchdog...
[PASS] Linux: lux-runner-linux is running
[PASS] Windows: lux-runner-windows is running
[INFO] Check interval: 30 seconds
```

If a VM stops:
```
[FAIL] Windows: lux-runner-windows is stopped
[ALERT] Alert would be sent to @hermes: Windows FAILED: stopped unexpectedly
```

---

## Next Steps

1. Get the Pi IP address (run `ping pi3b.local` on your computer)
2. Confirm the Proxmox password is `nivaniva`
3. Reply with the details so I can generate the final working config
4. Set up the real-time dashboard view on the Pi

---

## Quick Reference

| Item | Value |
|------|-------|
| Pi IP | `pi3b.local` |
| Pi Username | `pi` |
| Proxmox Host | `pve.starbounded.com` |
| Proxmox User | `root` |
| Proxmox Password | `nivaniva` |
| VM Names | `lux-runner-linux`, `lux-runner-windows` |
| Watchdog Script | `/home/pi/watchdog.py` |
| Log File | `/home/pi/watchdog.log` |
| Service Name | `pi-watchdog` |
