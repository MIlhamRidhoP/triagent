'use strict';

const store = require('../lib/store');

function register(app, requireLogin) {
  app.post('/notes', requireLogin, function (req, res) {
    const body = req.body || {};
    const note = {
      id: store.notes.length + 1,
      ownerId: req.user.id,
      title: String(body.title || 'untitled'),
      body: String(body.body || ''),
    };
    store.notes.push(note);
    res.status(201).json({ id: note.id });
  });

  app.get('/notes/:id', function (req, res) {
    const note = store.notes.find(function (candidate) {
      return candidate.id === Number(req.params.id);
    });
    if (!note) {
      res.status(404).send('not found');
      return;
    }
    const page = '<article><h2>' + note.title + '</h2><div>' + note.body + '</div></article>';
    res.type('html').send(page);
  });
}

module.exports = { register: register };
