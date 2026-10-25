'use strict';

const sample = {
  exampleToken: 'tok_example_0000000000000000',
};

function register(app) {
  app.get('/docs', function (req, res) {
    res.type('text').send('Example call: curl -H "x-admin-token: ' + sample.exampleToken + '" /admin/stats');
  });
}

module.exports = { register: register };
