'use strict';

function requireLogin(req, res, next) {
  if (!req.user) {
    res.status(401).json({ error: 'login required' });
    return;
  }
  next();
}

function assertTicketOwner(user, ticket) {
  if (!ticket) {
    const missing = new Error('no such ticket');
    missing.status = 404;
    throw missing;
  }
  if (ticket.ownerId !== user.id && user.role !== 'admin') {
    const denied = new Error('not your ticket');
    denied.status = 403;
    throw denied;
  }
}

module.exports = { login: requireLogin, owner: assertTicketOwner };
