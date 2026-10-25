'use strict';

const path = require('path');

module.exports = {
  publicDir: path.join(__dirname, 'data', 'public'),
  adminToken: 'tdk-admin-7f3a91c2e8b64d05',
  previewHosts: ['docs.example.test'],
  redirectHosts: ['app.local'],
};
