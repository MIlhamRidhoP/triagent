'use strict';

const store = require('../lib/store');
const authz = require('../lib/authz');

function register(app, requireLogin) {
  app.get('/api/tickets/:id', requireLogin, function (req, res) {
    const ticket = store.findTicket(Number(req.params.id));
    if (!ticket) {
      res.status(404).json({ error: 'no such ticket' });
      return;
    }
    res.json(ticket);
  });

  app.get('/api/tickets/:id/details', requireLogin, function (req, res, next) {
    const ticket = store.findTicket(Number(req.params.id));
    try {
      authz.owner(req.user, ticket);
    } catch (err) {
      next(err);
      return;
    }
    res.json(ticket);
  });
}

module.exports = { register: register };
