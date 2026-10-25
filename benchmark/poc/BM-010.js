'use strict';

const poc = require('./lib/common');

// BM-010: missing authorization on /admin/export (a normal user gets the admin export).
poc.run(async function () {
  const token = await poc.login('alice');
  const res = await poc.request('GET', '/admin/export', { headers: poc.bearer(token) });
  poc.finish(res.status === 200 && res.body.includes('admin-private-note'), 'status ' + res.status + ' as a non-admin user');
});
