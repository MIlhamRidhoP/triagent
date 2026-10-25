'use strict';

const crypto = require('crypto');
const minisql = require('./minisql');

function hashPassword(plain) {
  return crypto.createHash('sha256').update('fieldnotes:' + plain).digest('hex');
}

const users = [
  { id: 1, name: 'alice', role: 'user', email: 'alice@example.test', apiNote: 'alice-private-note' },
  { id: 2, name: 'bob', role: 'user', email: 'bob@example.test', apiNote: 'bob-private-note' },
  { id: 3, name: 'admin', role: 'admin', email: 'admin@example.test', apiNote: 'admin-private-note' },
];

const passwords = new Map([
  [1, hashPassword('alice-pw')],
  [2, hashPassword('bob-pw')],
  [3, hashPassword('admin-pw')],
]);

const tickets = [
  { id: 1, ownerId: 1, title: 'Printer jam', body: 'The third floor printer eats paper.' },
  { id: 2, ownerId: 2, title: 'VPN down', body: 'Reset requested, reference secret-TICKET-2.' },
];

const notes = [
  { id: 1, ownerId: 1, title: 'Welcome note', body: 'Be kind to the build server.' },
];

const sessions = new Map();

const db = new minisql.Database();
db.createTable('users', users);

function findTicket(id) {
  return tickets.find(function (candidate) {
    return candidate.id === id;
  });
}

function login(name, plain) {
  const user = users.find(function (candidate) {
    return candidate.name === name;
  });
  if (!user || passwords.get(user.id) !== hashPassword(plain)) {
    return null;
  }
  const token = crypto.randomBytes(16).toString('hex');
  sessions.set(token, user);
  return token;
}

module.exports = {
  users: users,
  tickets: tickets,
  notes: notes,
  sessions: sessions,
  preferences: {},
  settings: {},
  db: db,
  findTicket: findTicket,
  login: login,
};
