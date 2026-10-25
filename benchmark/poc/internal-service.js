'use strict';

// Stand-in for a service that exists only inside the isolated benchmark network (target of the SSRF items).
const http = require('http');

http
  .createServer(function (req, res) {
    if (req.url === '/latest/meta') {
      res.end('INTERNAL-ONLY-7c1e: metadata that must never leave the internal network\n');
      return;
    }
    res.statusCode = 404;
    res.end('not found\n');
  })
  .listen(8081, '0.0.0.0');
process.on('SIGTERM', function () {
  process.exit(0);
});
