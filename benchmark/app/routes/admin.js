'use strict';

const store = require('../lib/store');
const config = require('../config');

function register(app, requireLogin) {
  app.get('/admin/stats', function (req, res) {
    if (req.get('x-admin-token') !== config.adminToken) {
      res.status(403).json({ error: 'forbidden' });
      return;
    }
    res.json({ users: store.users.length, tickets: store.tickets.length });
  });

  // Admin dashboard export. The gateway in front of the service restricts this path to staff.
  app.get('/admin/export', requireLogin, function (req, res) {
    res.json({ users: store.users });
  });
}

module.exports = { register: register };
