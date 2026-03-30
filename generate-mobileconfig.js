// Generates caddy-trust.mobileconfig from the local Caddy root CA.
// Called by start-servers.bat after Caddy has run at least once.
const fs = require('fs');
const path = require('path');

const appData = process.env.APPDATA || '';
const certPath = path.join(appData, 'Caddy', 'pki', 'authorities', 'local', 'root.crt');
const outPath = path.join(__dirname, 'wwwroot', 'caddy-trust.mobileconfig');

if (!fs.existsSync(certPath)) {
  console.log('Caddy root CA not found at: ' + certPath);
  console.log('Start Caddy once first so it generates its certificate.');
  process.exit(1);
}

// Read PEM cert, convert to DER (base64 inner content)
const pem = fs.readFileSync(certPath, 'utf8');
const b64 = pem.replace(/-----BEGIN CERTIFICATE-----/, '')
              .replace(/-----END CERTIFICATE-----/, '')
              .replace(/\s/g, '');

// Wrap in base64 lines of 76 chars
const b64Lines = b64.match(/.{1,76}/g).join('\n');

const mobileconfig = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadCertificateFileName</key>
            <string>CaddyLocalAuthority.crt</string>
            <key>PayloadContent</key>
            <data>
${b64Lines}
            </data>
            <key>PayloadDescription</key>
            <string>Adds Caddy Local Authority root CA for LAN HTTPS</string>
            <key>PayloadDisplayName</key>
            <string>Caddy Local Authority Root CA</string>
            <key>PayloadIdentifier</key>
            <string>com.explorestarlite.caddy-root</string>
            <key>PayloadType</key>
            <string>com.apple.security.root</string>
            <key>PayloadUUID</key>
            <string>A1B2C3D4-E5F6-7890-ABCD-EF1234567890</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>ExplorestarsLite HTTPS</string>
    <key>PayloadDescription</key>
    <string>Trust Caddy Local Authority for ExplorestarsLite LAN HTTPS access</string>
    <key>PayloadIdentifier</key>
    <string>com.explorestarlite.https-profile</string>
    <key>PayloadOrganization</key>
    <string>ExplorestarsLite</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>B2C3D4E5-F6A7-8901-BCDE-F12345678901</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>`;

fs.writeFileSync(outPath, mobileconfig, 'utf8');
console.log('Generated: ' + outPath);
