'use strict';

const poc = require('./lib/common');

// BM-018 (trap): execFile with an argument array, the shell never sees the text.
poc.run(async function () {
  const normal = await poc.request('GET', '/tools/say?' + poc.query({ msg: 'hello' }));
  poc.control(normal.body.trim() === 'hello', 'plain echo works');
  const res = await poc.request('GET', '/tools/say?' + poc.query({ msg: 'x;echo $((6*7))QQ' }));
  poc.finish(res.body.includes('42QQ'), 'output ' + JSON.stringify(res.body.slice(0, 80)));
});
