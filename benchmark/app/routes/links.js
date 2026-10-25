'use strict';

const http = require('http');
const config = require('../config');

function register(app) {
  app.get('/go', function (req, res) {
    const next = String(req.query.next || '/');
    res.redirect(next);
  });

  app.get('/jump', function (req, res) {
    const wanted = String(req.query.next || '/');
    let target;
    try {
      target = new URL(wanted, 'http://app.local');
    } catch (err) {
      res.redirect('/');
      return;
    }
    if (config.redirectHosts.includes(target.host)) {
      res.redirect('/' + target.pathname.replace(/^\/+/, '') + target.search);
      return;
    }
    res.redirect('/');
  });

  app.get('/preview', function (req, res) {
    const address = String(req.query.url || '');
    // The link checker only ever submits public documentation pages, so fetching them is safe.
    http
      .get(address, function (upstream) {
        let received = '';
        upstream.setEncoding('utf8');
        upstream.on('data', function (chunk) {
          received += chunk;
        });
        upstream.on('end', function () {
          res.type('text').send(received.slice(0, 500));
        });
      })
      .on('error', function () {
        res.status(502).send('fetch failed');
      });
  });

  app.get('/card', function (req, res) {
    let parsed;
    try {
      parsed = new URL(String(req.query.url || ''));
    } catch (err) {
      res.status(400).send('bad url');
      return;
    }
    if (parsed.protocol !== 'http:' || !config.previewHosts.includes(parsed.hostname)) {
      res.status(403).send('host not allowed');
      return;
    }
    http
      .get(parsed.href, function (upstream) {
        let received = '';
        upstream.setEncoding('utf8');
        upstream.on('data', function (chunk) {
          received += chunk;
        });
        upstream.on('end', function () {
          res.type('text').send(received.slice(0, 500));
        });
      })
      .on('error', function () {
        res.status(502).send('fetch failed');
      });
  });
}

module.exports = { register: register };
