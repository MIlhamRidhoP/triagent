'use strict';

const store = require('../lib/store');
const html = require('../lib/html');

function register(app) {
  app.get('/search', function (req, res) {
    const term = String(req.query.q || '');
    const hits = store.notes.filter(function (note) {
      return note.title.toLowerCase().includes(term.toLowerCase());
    });
    const list =
      '<ul>' +
      hits
        .map(function (note) {
          return '<li>' + html.escape(note.title) + '</li>';
        })
        .join('') +
      '</ul>';
    res.type('html').send('<h1>Results for ' + term + '</h1>' + list);
  });
}

module.exports = { register: register };
