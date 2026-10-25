'use strict';

const poc = require('./lib/common');

// BM-022 (trap): the example token in config.js is only documentation, the server rejects it.
const fs = require('fs');

poc.run(async function () {
  const source = fs.readFileSync('/app/routes/docs.js', 'utf8');
  const found = /exampleToken:\s*['"]([^'"]+)['"]/.exec(source);
  poc.control(found !== null, 'example token pattern found in config.js');
  const docs = await poc.request('GET', '/docs');
  poc.control(docs.body.includes(found[1]), 'docs page shows the example token');
  const res = await poc.request('GET', '/admin/stats', { headers: { 'x-admin-token': found[1] } });
  poc.finish(res.status === 200, 'status ' + res.status + ' with the example token');
});
