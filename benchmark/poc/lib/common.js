'use strict';

// Shared helpers for the benchmark PoC scripts. A PoC only ever talks to the benchmark app
// inside the isolated benchmark network. Exit codes: 0 exploit confirmed, 1 not reproduced,
// 2 harness error. The last line printed on stdout is a JSON verdict.

const http = require('http');

const BASE = process.env.TARGET_URL || 'http://app:3000';
let attempts = 0;

function rawRequest(method, target, options) {
  const opts = options || {};
  return new Promise(function (resolve, reject) {
    const url = new URL(target, BASE);
    let body = null;
    if (opts.body !== undefined) {
      body = typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body);
    }
    const headers = Object.assign({}, opts.headers || {});
    if (body !== null) {
      headers['content-type'] = headers['content-type'] || 'application/json';
      headers['content-length'] = Buffer.byteLength(body);
    }
    const req = http.request(
      {
        method: method,
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        headers: headers,
        timeout: 10000,
      },
      function (res) {
        let text = '';
        res.setEncoding('utf8');
        res.on('data', function (chunk) {
          text += chunk;
        });
        res.on('end', function () {
          resolve({ status: res.statusCode, headers: res.headers, body: text });
        });
      },
    );
    req.on('timeout', function () {
      req.destroy(new Error('request timed out'));
    });
    req.on('error', reject);
    if (body !== null) {
      req.write(body);
    }
    req.end();
  });
}

function request(method, target, options) {
  attempts += 1;
  return rawRequest(method, target, options);
}

function query(params) {
  return new URLSearchParams(params).toString();
}

function sleep(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms);
  });
}

async function ready() {
  for (let i = 0; i < 100; i += 1) {
    try {
      const res = await rawRequest('GET', '/health');
      if (res.status === 200) {
        return;
      }
    } catch (err) {
      // the app is still starting
    }
    await sleep(300);
  }
  throw new Error('target never became ready');
}

async function login(username) {
  const res = await request('POST', '/login', { body: { username: username, password: username + '-pw' } });
  if (res.status !== 200) {
    throw new Error('login failed for ' + username);
  }
  return JSON.parse(res.body).token;
}

function bearer(token) {
  return { authorization: 'Bearer ' + token };
}

function finish(exploited, evidence) {
  const line = JSON.stringify({ exploited: exploited, attempts: attempts, evidence: evidence });
  process.stdout.write(line + '\n', function () {
    process.exit(exploited ? 0 : 1);
  });
}

function control(condition, message) {
  if (!condition) {
    throw new Error('control check failed: ' + message);
  }
}

function run(main) {
  ready()
    .then(main)
    .catch(function (err) {
      process.stderr.write(String((err && err.stack) || err) + '\n');
      process.exit(2);
    });
}

module.exports = {
  request: request,
  query: query,
  login: login,
  bearer: bearer,
  finish: finish,
  control: control,
  run: run,
};
