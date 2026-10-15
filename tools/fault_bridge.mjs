// Live ntfy -> GitHub issue -> project queue. Config and durable state live outside the repo.
import fs from 'node:fs';
import http from 'node:http';
import { pathToFileURL } from 'node:url';

export async function forward(message, state, config, request = fetch) {
  const match = /^funny-furries\/(\d+\.\d+\.\d+) (Linux|Windows) (launcher|import|game|probe) fault$/.exec(message);
  if (!match) return false; // Public input never becomes instructions or arbitrary issue content.
  if (match[3] === 'probe') { state.probes = (state.probes || 0) + 1; return true; }
  const key = match.slice(1).join(' ');
  state.seen ||= {};
  if (state.seen[key]) return true;
  state.sent = (state.sent || []).filter(t => t > Date.now() - 3600000);
  if (state.sent.length >= 3) return false;
  const title = `[fault] Funny Furries ${key}`;
  async function github(path, body) {
    const response = await request((config.githubApi || 'https://api.github.com') + '/repos/jarvis-jhk/funny-furries/' + path, {
      method: body ? 'POST' : 'GET', headers: { authorization: `Bearer ${config.githubToken}`, 'content-type': 'application/json', 'user-agent': 'funny-furries-fault-relay' },
      body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error(`GitHub ${response.status}`);
    return response.json();
  }
  const issues = await github('issues?state=open&per_page=100');
  let issue = issues.find(i => i.title === title && !i.pull_request);
  if (!issue) issue = await github('issues', { title, body: 'Anonymous release fault received through the public ntfy relay.\n\nApp version, OS and category only:\n\n' + message + '\n\nNo logs, player paths, identities or original content were transmitted. Reproduce locally; this is not hardware acceptance evidence.' });
  const response = await request(config.reportUrl, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ lane: 'furries', kind: 'bug', title, detail: issue.html_url + '\n' + message,
      source: 'Funny Furries anonymous fault relay' }), signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`Project queue ${response.status}`);
  state.seen[key] = issue.number;
  state.sent.push(Date.now());
  return true;
}

async function main() {
  const config = JSON.parse(fs.readFileSync(new URL('./config.json', import.meta.url)));
  const stateFile = new URL('./state.json', import.meta.url);
  let state = { lastId: null, seen: {}, pending: [], probes: 0 };
  try { state = { ...state, ...JSON.parse(fs.readFileSync(stateFile)) }; } catch {}
  const save = () => { fs.writeFileSync(new URL('./state.tmp', import.meta.url), JSON.stringify(state)); fs.renameSync(new URL('./state.tmp', import.meta.url), stateFile); };
  let connected = false;
  let lastError = '';
  let flushing = false;
  let lastOwnFault = 0;
  function ownFault() {
    if (Date.now() - lastOwnFault < 3600000) return;
    lastOwnFault = Date.now();
    fetch(config.reportUrl, {method: 'POST', headers: {'content-type': 'application/json'},
      body: JSON.stringify({lane: 'furries', kind: 'bug', title: 'Funny Furries fault relay failed',
        detail: 'Fault relay could not complete its background transport; inspect its local health and logs.',
        source: 'Funny Furries fault relay'}), signal: AbortSignal.timeout(10000)}).catch(() => {});
  }

  async function flush() {
    if (flushing) return;
    flushing = true;
    try {
      while (state.pending.length) {
        if (!await forward(state.pending[0], state, config)) {
          // Invalid messages can be discarded; valid rate-limited ones wait durably.
          if (/^funny-furries\/\d+\.\d+\.\d+ (Linux|Windows) (launcher|import|game) fault$/.test(state.pending[0])) break;
        }
        state.pending.shift(); save();
      }
      lastError = '';
    } catch (error) { lastError = error.message; console.error(lastError); ownFault(); }
    finally { flushing = false; }
  }
  setInterval(flush, 10000).unref();
  http.createServer((req, res) => {
    // Health contains no public payloads, paths or credentials.
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ connected, pending: state.pending.length, issues: Object.keys(state.seen).length, probes: state.probes, lastError }));
  }).listen(Number(process.env.PORT), '127.0.0.1');
  for (;;) {
    try {
      const response = await fetch('https://ntfy.sh/funny-furries-faults-a93c6b4e12d8/json?since=' + (state.lastId || '12h'));
      if (!response.ok) throw new Error(`ntfy ${response.status}`);
      connected = true;
      let buffer = '';
      for await (const chunk of response.body) {
        buffer += Buffer.from(chunk).toString();
        let newline;
        while ((newline = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
          if (!line.trim()) continue;
          const message = JSON.parse(line);
          if (message.event !== 'message') continue;
          if (typeof message.message === 'string' && message.message.length < 100 && state.pending.length < 40) state.pending.push(message.message);
          state.lastId = message.id; save();
          await flush();
        }
      }
    } catch (error) { lastError = error.message; console.error(lastError); ownFault(); }
    connected = false;
    await new Promise(resolve => setTimeout(resolve, 10000));
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main().catch(error => { console.error(error.message); process.exit(1); });
