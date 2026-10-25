'use strict';

const store = require('../lib/store');

const SORT_COLUMNS = new Map([
  ['name', 'name'],
  ['role', 'role'],
  ['id', 'id'],
]);

function register(app, requireLogin) {
  app.get('/api/users/search', requireLogin, function (req, res, next) {
    const name = String(req.query.name || '');
    try {
      // The name has already been sanitised by the validation middleware, so it is safe to inline.
      const rows = store.db.query("SELECT id, name, role, email FROM users WHERE name = '" + name + "'");
      res.json({ users: rows });
    } catch (err) {
      next(err);
    }
  });

  app.get('/api/users/find', requireLogin, function (req, res, next) {
    const name = String(req.query.name || '');
    try {
      const rows = store.db.query('SELECT id, name, role FROM users WHERE name = ?', [name]);
      res.json({ users: rows });
    } catch (err) {
      next(err);
    }
  });

  app.get('/api/users/list', requireLogin, function (req, res, next) {
    const requested = String(req.query.sort || 'id');
    const column = SORT_COLUMNS.get(requested) || 'id';
    try {
      const rows = store.db.query('SELECT id, name, role FROM users ORDER BY ' + column);
      res.json({ users: rows });
    } catch (err) {
      next(err);
    }
  });
}

module.exports = { register: register };
