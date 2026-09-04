import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSnapshot } from '../src/snapshot.js';

test('accepts a browser-session snapshot', () => {
  const data = { source: 'rally-browser-session', stories: [{ ObjectID: 1, FormattedID: 'US1', _tasks: [] }] };
  assert.equal(validateSnapshot(data), data);
});

test('rejects unsupported snapshot source', () => {
  assert.throws(() => validateSnapshot({ source: 'other', stories: [] }), /Unsupported snapshot source/);
});

test('requires Rally identifiers', () => {
  assert.throws(() => validateSnapshot({ source: 'rally-browser-session', stories: [{}] }), /ObjectID and FormattedID/);
});
