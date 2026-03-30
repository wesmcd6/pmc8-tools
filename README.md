# ExplorestarsLite PWA Server

Control your Explore Scientific PMC-Eight telescope mount from your iPhone or Android phone — no app install needed. Just a PC on the same WiFi network.

## Quick Start

1. **Install two free programs** on your Windows PC:
   - [Node.js](https://nodejs.org) — click the big green **LTS** button, run the installer
   - [Caddy](https://caddyserver.com/download) — select **Windows amd64**, download, rename to `caddy.exe`, put it in `C:\caddy\`

2. **Download this package:**
   - **[Click here to download the ZIP](https://github.com/wesmcd6/pmc8-tools/archive/refs/heads/pwa-server.zip)**
   - Extract the ZIP to any folder (e.g., `C:\ExplorestarsLite`)

3. **Start the server:**
   - Double-click `start-servers.bat`
   - It shows your PC's IP address and starts the server

4. **Open on your phone:**
   - Connect your phone to the same WiFi as the PC
   - Open Safari (iPhone) or Chrome (Android)
   - Go to `http://<your-pc-ip>:5257` (the address shown in the server window)

That's it. The app runs in your phone's browser.

## Guides

Right-click each link below and choose **"Save link as..."** to download, then open the saved file in your browser:

- **[Server Setup Guide](https://raw.githubusercontent.com/wesmcd6/pmc8-tools/pwa-server/docs/server-setup-guide.html)** — detailed step-by-step instructions with troubleshooting
- **[iPhone HTTPS Setup](https://raw.githubusercontent.com/wesmcd6/pmc8-tools/pwa-server/docs/iphone-https-setup.html)** — install the certificate for polar alignment (compass access requires HTTPS)

These guides are also included in the ZIP download (in the `docs` folder).

## What's in the Box

| File | What it does |
|------|-------------|
| `start-servers.bat` | Double-click to start everything |
| `wwwroot/` | The ExplorestarsLite app (pre-built, ready to serve) |
| `mount-proxy.js` | Routes mount commands through HTTPS |
| `Caddyfile` | Web server configuration |
| `docs/` | Setup guides |

## Requirements

- **Windows PC** with WiFi (or Ethernet on the same network)
- **Node.js** (free, any version 18+)
- **Caddy** (free, single exe, no install)
- **Phone** on the same WiFi network
- **PMC-Eight mount** on the same WiFi network

No .NET, no Visual Studio, no coding. Just download, double-click, and go.

## HTTPS (Optional)

HTTPS is only needed if you want compass access on iPhone (for polar alignment). For normal mount control — GoTo, tracking, slewing, search — plain HTTP works fine.

If you need HTTPS, see the [iPhone HTTPS Setup](docs/iphone-https-setup.html) guide.
