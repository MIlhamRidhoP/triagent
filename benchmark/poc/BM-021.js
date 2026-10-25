'use strict';

const poc = require('./lib/common');

// BM-021 (trap): /api/tickets/:id/details checks ownership, alice cannot read bob's ticket here.
poc.run(async function () {
  const token = await poc.login('alice');
  const headers = poc.bearer(token);
  const own = await poc.request('GET', '/api/tickets/1/details', { headers: headers });
  poc.control(own.status === 200, 'own ticket readable');
  const res = await poc.request('GET', '/api/tickets/2/details', { headers: headers });
  poc.finish(res.status === 200 && res.body.includes('secret-TICKET-2'), 'status ' + res.status + ' reading ticket 2 as alice');
});
