'use strict';

const poc = require('./lib/common');

// BM-017 (trap): /files/view resolves the path and refuses anything outside the public directory.
poc.run(async function () {
  const normal = await poc.request('GET', '/files/view?' + poc.query({ name: 'welcome.txt' }));
  poc.control(normal.status === 200 && normal.body.includes('Welcome to Fieldnotes'), 'plain view works');
  let leaked = false;
  let seen = '';
  for (const name of ['../private/flag.txt', '..%2Fprivate%2Fflag.txt', '/app/data/private/flag.txt']) {
    const res = await poc.request('GET', '/files/view?' + poc.query({ name: name }));
    seen += name + ' => ' + res.status + '; ';
    if (res.body.includes('FLAG-PRIVATE-8842')) {
      leaked = true;
    }
  }
  poc.finish(leaked, seen);
});
