'use strict';

const poc = require('./lib/common');

// BM-023 (trap): /api/settings merges with a key blocklist, so the prototype is not reachable.
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  const before = await poc.request('GET', '/api/flags');
  poc.control(JSON.parse(before.body).debugMode === false, 'flag starts false');
  await poc.request('POST', '/api/settings', { headers: headers, body: '{"__proto__":{"debugMode":true}}' });
  await poc.request('POST', '/api/settings', { headers: headers, body: '{"constructor":{"prototype":{"debugMode":true}}}' });
  const after = await poc.request('GET', '/api/flags');
  poc.finish(JSON.parse(after.body).debugMode === true, 'debugMode after attempts: ' + JSON.parse(after.body).debugMode);
});
