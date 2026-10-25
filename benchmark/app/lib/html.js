'use strict';

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, function (ch) {
    return ESCAPES[ch];
  });
}

module.exports = { escape: escapeHtml };
