'use strict';

const html = require('../lib/html');

function register(app) {
  app.get('/greet', function (req, res) {
    const visitor = String(req.query.name || 'guest');
    // SECURITY: the visitor name is echoed into the page without any escaping (reflected XSS).
    res.type('html').send('<p>Hello, ' + html.escape(visitor) + '!</p>');
  });
}

module.exports = { register: register };
