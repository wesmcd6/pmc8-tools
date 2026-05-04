# ExploreStars Envision&trade; PWA Server

Control your Explore Scientific&trade; PMC-Eight&trade; telescope mount from your iPhone or Android phone — no app install needed. Just a **Windows, macOS, or Linux PC** on the same WiFi network.

## Download

📦 **[Get the latest PWA-server zip from the Releases page →](../../releases/latest)**

Look for the asset named:

> `ExploreStars-Envision-vX.Y.Z.W-pwa-server.zip`

The zip contains everything you need: pre-built Blazor WASM `wwwroot/`, Caddy config, mount proxy, the Windows `start-servers.bat` and the Linux/macOS `start-servers.sh`, and the setup guides in `docs/`.

After downloading, extract (unzip) to a folder of your choice — for example, `C:\ExploreStars-Envision` on Windows, or `~/ExploreStars-Envision` on Linux/macOS.

## How to Get Started

After extracting, open `docs/server-setup-guide.html` in your web browser. The guide walks you through:

- Installing the two required free programs (Node.js and Caddy) — **you must do this before the server will work**
- Starting the server
- Connecting from your phone
- Connecting to your PMC-Eight mount
- Troubleshooting

The guide has Windows-focused steps with a separate **Linux / macOS** section that walks through the equivalent commands.

## Requirements

- **Windows, macOS, or Linux PC** with WiFi (or Ethernet on the same network)
- **Node.js** — free, installed by following the setup guide
- **Caddy** — free, installed by following the setup guide
- **Phone** on the same WiFi network
- **PMC-Eight mount** on the same WiFi network

No programming or coding knowledge required.

## Why is this branch empty?

This branch used to ship the entire bundle (`wwwroot/`, `Caddyfile`, scripts, `docs/`) directly. As of v2.1.0.2 it's a thin pointer — the bundle lives on the [GitHub Releases page](../../releases/latest), where versioning, changelogs, and historical builds are handled natively.

The Releases page also keeps every prior version available, so if you need a specific older build you can pick it from the [release list](../../releases).
