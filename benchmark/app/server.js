'use strict';

// INTENTIONALLY VULNERABLE benchmark application. Never run it outside the isolated benchmark
// containers started by `triagent benchmark poc`, and never expose it to an open network.

const express = require('express');
const store = require('./lib/store');
const authz = require('./lib/authz');

const app = express();
app.disable('x-powered-by');
app.use(express.json());

app.use(function (req, res, next) {
  const header = req.get('authorization') || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  req.user = store.sessions.get(token) || null;
  next();
});

app.get('/health', function (req, res) {
  res.json({ ok: true });
});

app.post('/login', function (req, res) {
  const body = req.body || {};
  const token = store.login(String(body.username || ''), String(body.password || ''));
  if (!token) {
    res.status(401).json({ error: 'bad credentials' });
    return;
  }
  res.json({ token: token });
});

require('./routes/search').register(app);
require('./routes/home').register(app);
require('./routes/docs').register(app);
require('./routes/notes').register(app, authz.login);
require('./routes/users').register(app, authz.login);
require('./routes/files').register(app);
require('./routes/tools').register(app);
require('./routes/links').register(app);
require('./routes/tickets').register(app, authz.login);
require('./routes/admin').register(app, authz.login);
require('./routes/profile').register(app, authz.login);

app.use(function (err, req, res, next) {
  res.status(err.status || 500).json({ error: err.status ? err.message : 'internal error' });
});

if (require.main === module) {
  if (process.env.BENCHMARK_SANDBOX !== '1') {
    console.error('refusing to start: this application is intentionally vulnerable');
    process.exit(1);
  }
  const port = Number(process.env.PORT || 3000);
  const host = process.env.HOST || '127.0.0.1';
  app.listen(port, host, function () {
    console.log('fieldnotes-bench listening on ' + host + ':' + port);
  });
  process.on('SIGTERM', function () {
    process.exit(0);
  });
}

module.exports = app;
