'use strict';

// Isolation self-test. Baked into the image at /opt/selftest and run INSIDE both the PoC and the
// app container (never on the host). Every key is true when the container is properly isolated.
// BENCH_GATEWAY_IP (the bench network gateway, read by the host) is passed in the environment.
const dns = require('dns');
const fs = require('fs');
const http = require('http');
const net = require('net');

const GATEWAY = process.env.BENCH_GATEWAY_IP || '';
const TARGET = process.env.SELFTEST_TARGET || 'http://app:3000';

function blocked(host, port) {
  return new Promise(function (resolve) {
    const socket = net.connect({ host: host, port: port });
    socket.setTimeout(2500);
    socket.on('connect', function () {
      socket.destroy();
      resolve(false);
    });
    socket.on('timeout', function () {
      socket.destroy();
      resolve(true);
    });
    socket.on('error', function () {
      resolve(true);
    });
  });
}

function unresolved(name) {
  return new Promise(function (resolve) {
    dns.lookup(name, function (err) {
      resolve(Boolean(err));
    });
  });
}

function writeFails(target) {
  try {
    fs.writeFileSync(target, 'x');
    fs.unlinkSync(target);
    return false;
  } catch (err) {
    return true;
  }
}

function get(url, headers, body) {
  return new Promise(function (resolve) {
    const parsed = new URL(url);
    const req = http.request(
      {
        method: body === undefined ? 'GET' : 'POST',
        hostname: parsed.hostname,
        port: parsed.port,
        path: parsed.pathname + parsed.search,
        headers: Object.assign({}, headers || {}),
        timeout: 4000,
      },
      function (res) {
        let text = '';
        res.setEncoding('utf8');
        res.on('data', function (chunk) {
          text += chunk;
        });
        res.on('end', function () {
          resolve({ status: res.statusCode, body: text });
        });
      },
    );
    req.on('error', function () {
      resolve({ status: 0, body: '' });
    });
    req.on('timeout', function () {
      req.destroy();
    });
    if (body !== undefined) {
      req.write(body);
    }
    req.end();
  });
}

function noDefaultRoute() {
  try {
    const lines = fs.readFileSync('/proc/net/route', 'utf8').split('\n').slice(1);
    return !lines.some(function (line) {
      const cols = line.trim().split(/\s+/);
      return cols.length > 1 && cols[1] === '00000000';
    });
  } catch (err) {
    return false;
  }
}

async function errorNoLeak() {
  const body = JSON.stringify({ username: 'alice', password: 'alice-pw' });
  const login = await get(TARGET + '/login', { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) }, body);
  if (login.status !== 200) {
    return false;
  }
  const token = JSON.parse(login.body).token;
  const res = await get(TARGET + '/api/users/search?name=%27', { authorization: 'Bearer ' + token });
  return res.status === 500 && !/SQL|syntax|unterminated/i.test(res.body);
}

async function main() {
  let reachable = false;
  for (let i = 0; i < 40 && !reachable; i += 1) {
    reachable = (await get(TARGET + '/health')).status === 200;
    if (!reachable) {
      await new Promise(function (resolve) {
        setTimeout(resolve, 500);
      });
    }
  }
  const gatewayPorts = GATEWAY
    ? await Promise.all([22, 80, 2375, 2376, 3000].map(function (port) { return blocked(GATEWAY, port); }))
    : [false];
  const result = {
    egress_ip_blocked: (await blocked('1.1.1.1', 443)) && (await blocked('8.8.8.8', 53)),
    egress_dns_blocked: await unresolved('example.com'),
    non_root: typeof process.getuid === 'function' && process.getuid() !== 0,
    rootfs_read_only: writeFails('/selftest-write-probe') && writeFails('/etc/selftest-write-probe'),
    source_mount_read_only: writeFails('/app/selftest-write-probe'),
    no_default_route: noDefaultRoute(),
    gateway_ports_blocked: gatewayPorts.every(Boolean),
    docker_tcp_blocked: await blocked('172.17.0.1', 2375),
    host_dns_blocked: (await unresolved('host.docker.internal')) && (await unresolved('gateway.docker.internal')),
    metadata_blocked: await blocked('169.254.169.254', 80),
    no_docker_sock: !fs.existsSync('/var/run/docker.sock'),
    control_reachable: reachable,
    error_no_leak: reachable ? await errorNoLeak() : false,
  };
  process.stdout.write(JSON.stringify(result) + '\n');
}

main().catch(function (err) {
  process.stderr.write(String(err) + '\n');
  process.exit(2);
});
