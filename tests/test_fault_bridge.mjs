import test from 'node:test';
import assert from 'node:assert/strict';
import { forward } from '../tools/fault_bridge.mjs';

test('fault relay validates, creates, forwards and deduplicates anonymous reports', async () => {
  const state = {};
  const config = { reportUrl: 'http://queue.invalid', githubToken: 'test-only' };
  const calls = [];
  const request = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => options.method === 'GET' ? [] : { number: 7, html_url: 'https://github.com/jarvis-jhk/funny-furries/issues/7' } };
  };
  assert.equal(await forward('arbitrary public text', state, config, request), false);
  assert.equal(calls.length, 0);
  assert.equal(await forward('funny-furries/0.1.0 Linux game fault', state, config, request), true);
  assert.equal(calls.length, 3);
  assert.equal(JSON.parse(calls[2].options.body).lane, 'furries');
  assert.equal(await forward('funny-furries/0.1.0 Linux game fault', state, config, request), true);
  assert.equal(calls.length, 3);
  assert.equal(await forward('funny-furries/0.1.0 Linux probe fault', state, config, request), true);
  assert.equal(state.probes, 1);
  assert.equal(calls.length, 3);
});

test('queue failure is retried without forgetting the report', async () => {
  const state = {};
  const request = async (url, options) => {
    if (url === 'http://queue.invalid') return { ok: false, status: 503 };
    return { ok: true, json: async () => [{ title: '[fault] Funny Furries 0.1.0 Windows import', number: 8, html_url: 'test' }] };
  };
  await assert.rejects(forward('funny-furries/0.1.0 Windows import fault', state, { reportUrl: 'http://queue.invalid' }, request), /503/);
  assert.deepEqual(state.seen, {});
});
