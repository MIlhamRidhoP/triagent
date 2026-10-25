'use strict';

const poc = require('./lib/common');

// BM-016 (trap): ORDER BY column comes from an allowlist, injected text falls back to the default.
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  const base = await poc.request('GET', '/api/users/list?' + poc.query({ sort: 'id' }), { headers: headers });
  poc.control(base.status === 200, 'plain sort works');
  const baseline = JSON.parse(base.body).users.map(function (row) { return row.id; }).join(',');
  let altered = false;
  let seen = '';
  for (const sort of ['id DESC', 'id DESC --', 'name, 1=1', 'nonexistent']) {
    const res = await poc.request('GET', '/api/users/list?' + poc.query({ sort: sort }), { headers: headers });
    const order = res.status === 200 ? JSON.parse(res.body).users.map(function (row) { return row.id; }).join(',') : 'status ' + res.status;
    seen += sort + ' => ' + order + '; ';
    if (order !== baseline) {
      altered = true;
    }
  }
  poc.finish(altered, seen);
});
