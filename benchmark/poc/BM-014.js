'use strict';

const poc = require('./lib/common');

// BM-014 (trap): /greet escapes its input, so the payload must not come back raw.
poc.run(async function () {
  const normal = await poc.request('GET', '/greet?' + poc.query({ name: 'Ada' }));
  poc.control(normal.body.includes('Hello, Ada!'), 'plain greeting works');
  const payload = '<script>alert(7313)</script>';
  const res = await poc.request('GET', '/greet?' + poc.query({ name: payload }));
  poc.finish(res.body.includes(payload), 'payload ' + (res.body.includes(payload) ? 'reflected raw' : 'escaped: ' + res.body.slice(0, 60)));
});
