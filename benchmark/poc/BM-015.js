'use strict';

const poc = require('./lib/common');

// BM-015 (trap): parameterized query, the injection string is only ever data.
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  const normal = await poc.request('GET', '/api/users/find?' + poc.query({ name: 'alice' }), { headers: headers });
  poc.control(JSON.parse(normal.body).users.length === 1, 'plain lookup returns one user');
  const injected = await poc.request('GET', '/api/users/find?' + poc.query({ name: "x' OR '1'='1" }), { headers: headers });
  const count = injected.status === 200 ? JSON.parse(injected.body).users.length : 0;
  poc.finish(count > 0 || injected.status >= 500, 'injected lookup returned ' + count + ' rows (status ' + injected.status + ')');
});
