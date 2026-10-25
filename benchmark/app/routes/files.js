'use strict';

const fs = require('fs');
const path = require('path');
const config = require('../config');

function register(app) {
  app.get('/files/download', function (req, res) {
    const name = String(req.query.name || 'welcome.txt');
    const target = path.join(config.publicDir, name);
    fs.readFile(target, 'utf8', function (err, content) {
      if (err) {
        res.status(404).send('not found');
        return;
      }
      res.type('text').send(content);
    });
  });

  app.get('/files/view', function (req, res) {
    const name = String(req.query.name || 'welcome.txt');
    const base = path.resolve(config.publicDir);
    const target = path.resolve(base, name);
    if (target !== base && !target.startsWith(base + path.sep)) {
      res.status(400).send('invalid name');
      return;
    }
    fs.readFile(target, 'utf8', function (err, content) {
      if (err) {
        res.status(404).send('not found');
        return;
      }
      res.type('text').send(content);
    });
  });
}

module.exports = { register: register };
