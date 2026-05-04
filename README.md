# ExploreStars Envision&trade; PWA Server

Control your Explore Scientific&trade; PMC-Eight&trade; telescope mount from your iPhone or Android phone — no app install needed. Just a **Windows, macOS, or Linux PC** on the same WiFi network.

## How to Get Started

### Step 1 — Download the ZIP

**[Click here to download](https://github.com/wesmcd6/pmc8-tools/archive/refs/heads/pwa-server.zip)**

After downloading, extract (unzip) it to a folder on your PC — for example, `C:\ExploreStars-Envision`.

### Step 2 — Open the Setup Guide and Follow It

Inside the extracted folder, open the `docs` folder and double-click **`server-setup-guide.html`**. It will open in your web browser.

This guide walks you through everything:
- Installing the two required free programs (Node.js and Caddy) — **you must do this before the server will work**
- Starting the server
- Connecting from your phone
- Connecting to your PMC-Eight mount
- Troubleshooting

**Follow the guide step by step.** It is written for beginners.

## What's in the Download

| File | What it does |
|------|-------------|
| `start-servers.bat` | **Windows** — double-click to start the server (after setup is complete) |
| `start-servers.sh` | **Linux / macOS** — run `./start-servers.sh` from a terminal |
| `wwwroot/` | The ExploreStars Envision app (pre-built, ready to serve) |
| `mount-proxy.js` | Handles mount commands over HTTPS |
| `Caddyfile` | Web server configuration |
| `docs/` | Setup guides (open in your browser) |

## Requirements

- **Windows, macOS, or Linux PC** with WiFi (or Ethernet on the same network)
- **Node.js** — free, installed by following the setup guide
- **Caddy** — free, installed by following the setup guide
- **Phone** on the same WiFi network
- **PMC-Eight mount** on the same WiFi network

No programming or coding knowledge required. The setup guide has Windows-focused steps with a separate **Linux / macOS** section that walks through the equivalent commands.
