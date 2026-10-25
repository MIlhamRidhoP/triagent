# Image for the INTENTIONALLY VULNERABLE benchmark app and its PoC scripts.
# Only dependencies are baked in (one network step: npm ci from the lock file). The app source
# and the PoC scripts are mounted read-only at run time, so mutated variants reuse this image.
# The base image is pinned by digest (review R-07); the tag below is only a readable label.
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293
WORKDIR /opt/deps
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY selftest.js /opt/selftest/selftest.js
ENV NODE_PATH=/opt/deps/node_modules
USER node
