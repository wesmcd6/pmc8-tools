// Tiny HTTP proxy for mixed-content mount commands on HTTPS.
// Caddy forwards /mount-proxy/{mountIp}/{path} here.
// This proxy strips the prefix and forwards to http://{mountIp}:80/{path}.
// Sends minimal headers — ESP32 HTTP parser is very basic.
const http = require('http');

const PORT = 5258;

const server = http.createServer((req, res) => {
  // URL: /mount-proxy/{ip}/{path}
  const match = req.url.match(/^\/mount-proxy\/(\d+\.\d+\.\d+\.\d+)(\/.*)?$/);
  if (!match) {
    res.writeHead(400);
    res.end('Bad request — expected /mount-proxy/{ip}/{path}');
    return;
  }

  const mountIp = match[1];
  const mountPath = match[2] || '/';

  // Collect request body
  const chunks = [];
  req.on('data', (chunk) => chunks.push(chunk));
  req.on('end', () => {
    const body = Buffer.concat(chunks);

    // Send minimal request to ESP32 — only essential headers
    const options = {
      hostname: mountIp,
      port: 80,
      path: mountPath,
      method: req.method,
      timeout: 5000,
      headers: {
        'Content-Length': body.length,
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      // Forward CORS headers for browser compatibility
      res.writeHead(proxyRes.statusCode, {
        'Content-Type': proxyRes.headers['content-type'] || 'text/plain',
        'Access-Control-Allow-Origin': '*',
      });
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
      if (!res.headersSent) {
        res.writeHead(502);
        res.end('Proxy error: ' + err.message);
      }
    });

    proxyReq.on('timeout', () => {
      proxyReq.destroy();
      if (!res.headersSent) {
        res.writeHead(504);
        res.end('Proxy timeout');
      }
    });

    proxyReq.end(body);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Mount proxy listening on 127.0.0.1:${PORT}`);
});
