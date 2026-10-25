'use strict';

const poc = require('./lib/common');

// BM-020 (trap): /card only fetches allowlisted hosts, so the internal service stays unreachable.
poc.run(async function () {
  let fetched = false;
  let seen = '';
  for (const url of [
    'http://internal:8081/latest/meta',
    'http://docs.example.test@internal:8081/latest/meta',
    'file:///etc/passwd',
  ]) {
    const res = await poc.request('GET', '/card?' + poc.query({ url: url }));
    seen += url + ' => ' + res.status + '; ';
    if (res.body.includes('INTERNAL-ONLY-7c1e')) {
      fetched = true;
    }
  }
  poc.finish(fetched, seen);
});
