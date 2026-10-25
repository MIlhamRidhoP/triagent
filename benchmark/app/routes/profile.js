'use strict';

const store = require('../lib/store');
const merge = require('../lib/merge');

function register(app, requireLogin) {
  app.get('/api/profile', requireLogin, function (req, res) {
    res.json(req.user);
  });

  app.patch('/api/profile', requireLogin, function (req, res) {
    Object.assign(req.user, req.body);
    res.json(req.user);
  });

  app.post('/api/preferences', requireLogin, function (req, res) {
    merge.deep(store.preferences, req.body || {});
    res.json({ saved: true });
  });

  app.post('/api/settings', requireLogin, function (req, res) {
    merge.settings(store.settings, req.body || {});
    res.json({ saved: true });
  });

  app.get('/api/flags', function (req, res) {
    const probe = {};
    res.json({ debugMode: probe.debugMode === true });
  });
}

module.exports = { register: register };
