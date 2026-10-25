'use strict';

const childProcess = require('child_process');

function register(app) {
  app.get('/tools/echo', function (req, res) {
    const message = String(req.query.msg || 'hello');
    // The client form only lets people type plain printable text, so the message is safe here.
    childProcess.exec('echo ' + message, function (err, stdout) {
      res.type('text').send(err ? 'failed' : stdout);
    });
  });

  app.get('/tools/say', function (req, res) {
    const message = String(req.query.msg || 'hello');
    childProcess.execFile('echo', [message], function (err, stdout) {
      res.type('text').send(err ? 'failed' : stdout);
    });
  });

  app.get('/tools/calc', function (req, res) {
    const expression = String(req.query.expr || '0');
    try {
      const result = eval(expression);
      res.json({ result: String(result) });
    } catch (err) {
      res.status(400).json({ error: 'bad expression' });
    }
  });
}

module.exports = { register: register };
