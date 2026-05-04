#!/bin/bash
#
# ExploreStars Envision PWA Server -- Linux / macOS launcher
#
# Original Ubuntu bash script contributed by Ignazio Pillitteri (with
# permission, see contributor-grants/ in the source repo). Cross-platform
# IP detection added so the same script works on macOS as well as Linux.
#
# Run from the same folder that contains start-servers.bat, Caddyfile,
# mount-proxy.js, and wwwroot/. Press Ctrl+C to stop the servers.

set -e

echo ""
echo "============================================"
echo "   ExploreStars Envision PWA Server"
echo "   (Linux / macOS)"
echo "============================================"
echo ""

# ---------------------------------------------------------------------
# 1. Prerequisite checks
# ---------------------------------------------------------------------
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found in PATH."
    echo "       Install from https://nodejs.org or your package manager."
    echo "       Examples:"
    echo "         Ubuntu/Debian: sudo apt install nodejs npm"
    echo "         macOS (Homebrew): brew install node"
    exit 1
fi

if ! command -v caddy &> /dev/null; then
    echo "ERROR: Caddy not found in PATH."
    echo "       Download the binary for your OS from https://caddyserver.com/download"
    echo "       (caddy_linux_amd64, caddy_darwin_arm64, caddy_darwin_amd64, etc.)"
    echo "       Rename to 'caddy', make executable (chmod +x), and put on your PATH"
    echo "       (e.g., ~/bin/ or /usr/local/bin/)."
    exit 1
fi

if [ ! -f "wwwroot/index.html" ]; then
    echo "ERROR: wwwroot folder not found."
    echo "       Make sure this script is in the same folder as wwwroot,"
    echo "       Caddyfile, and mount-proxy.js."
    exit 1
fi

# ---------------------------------------------------------------------
# 2. Detect local IP (cross-platform)
# ---------------------------------------------------------------------
# Linux: hostname -I (GNU coreutils extension, Linux-only)
PC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

# macOS fallback: query the default-route interface
if [ -z "$PC_IP" ]; then
    iface=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')
    [ -n "$iface" ] && PC_IP=$(ipconfig getifaddr "$iface" 2>/dev/null)
fi

# Last-ditch fallback: parse ifconfig (works on Linux and macOS,
# filtered to common LAN ranges so we skip loopback + virtual)
if [ -z "$PC_IP" ]; then
    PC_IP=$(ifconfig 2>/dev/null | awk '/inet /{print $2}' \
            | grep -v '^127\.' \
            | grep -E '^(192\.168|10\.|172\.)' | head -1)
fi

[ -z "$PC_IP" ] && PC_IP="<your-PC-IP>"

echo "Prerequisites OK"
echo ""
echo "Your PC IP address: $PC_IP"
echo ""
echo "Starting servers..."
echo ""

# ---------------------------------------------------------------------
# 3. Launch background processes (PIDs captured for cleanup)
# ---------------------------------------------------------------------
echo "[1/2] Starting mount proxy..."
node mount-proxy.js &
PROXY_PID=$!

echo "[2/2] Starting web server..."
caddy run --config Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Give Caddy a moment to bind and generate certs
sleep 3

# ---------------------------------------------------------------------
# 4. Generate iPhone certificate profile (first run only)
# ---------------------------------------------------------------------
if [ ! -f "wwwroot/caddy-trust.mobileconfig" ]; then
    node generate-mobileconfig.js
fi

echo ""
echo "============================================"
echo "   All servers started!"
echo "============================================"
echo ""
echo "   Open this address on your phone's browser:"
echo ""
echo "      http://$PC_IP:5257"
echo ""
echo "   For HTTPS (polar alignment on iPhone):"
echo ""
echo "      https://$PC_IP:5256"
echo ""
echo "      (Requires certificate install -- see docs folder)"
echo ""
echo "============================================"
echo "   Press [CTRL+C] to STOP the servers..."
echo "============================================"

# ---------------------------------------------------------------------
# 5. Cleanup on Ctrl+C
# ---------------------------------------------------------------------
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$PROXY_PID" "$CADDY_PID" 2>/dev/null
    echo "All servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Block on the background processes so the script doesn't exit
wait
