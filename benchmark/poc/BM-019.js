'use strict';

const poc = require('./lib/common');

// BM-019 (trap): /jump only redirects to local paths.
poc.run(async function () {
  const normal = await poc.request('GET', '/jump?' + poc.query({ next: '/notes/1' }));
  poc.control(String(normal.headers.location) === '/notes/1', 'local redirect works');
  let offsite = false;
  let seen = '';
  for (const next of ['https://evil.example/phish', '//evil.example', '//app.local//evil.example', '/\\evil.example']) {
    const res = await poc.request('GET', '/jump?' + poc.query({ next: next }));
    const where = String(res.headers.location || '');
    seen += next + ' => ' + where + '; ';
    if (!where.startsWith('/') || where.startsWith('//') || where.startsWith('/\\')) {
      offsite = true;
    }
  }
  poc.finish(offsite, seen);
});
