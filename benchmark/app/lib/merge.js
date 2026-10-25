'use strict';

function isObject(value) {
  return typeof value === 'object' && value !== null;
}

function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (isObject(source[key])) {
      if (!isObject(target[key])) {
        target[key] = {};
      }
      deepMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

const BLOCKED_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

function mergeSettings(target, source) {
  for (const key of Object.keys(source)) {
    if (BLOCKED_KEYS.has(key)) {
      continue;
    }
    if (isObject(source[key])) {
      if (!Object.prototype.hasOwnProperty.call(target, key) || !isObject(target[key])) {
        target[key] = {};
      }
      mergeSettings(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

module.exports = { deep: deepMerge, settings: mergeSettings };
