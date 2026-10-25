'use strict';

const poc = require('./lib/common');

// BM-007: open redirect in /go (the redirect is observed, never followed).
poc.run(async function () {
  const target = 'https://evil.example/phish';
  const res = await poc.request('GET', '/go?' + poc.query({ next: target }));
  const where = String(res.headers.location || '');
  poc.finish(res.status >= 300 && res.status < 400 && where === target, 'status ' + res.status + ', location ' + where);
});
