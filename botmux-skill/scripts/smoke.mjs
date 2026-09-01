import { createServer } from 'node:http';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawn } from 'node:child_process';
import readline from 'node:readline';

const temporary = await mkdtemp(join(tmpdir(), 'seele-mcp-'));
const token = 'smoke-secret';
let runCount = 0;

const bridge = createServer(async (request, response) => {
  const body = [];
  for await (const chunk of request) body.push(chunk);
  const authorized = request.headers.authorization === `Bearer ${token}`;
  if (!authorized) {
    response.writeHead(401, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ ok: false, error: 'unauthorized' }));
    return;
  }
  if (request.method === 'GET' && request.url === '/v1/workflows') {
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({
      ok: true,
      workflows: [{ name: '京东数据抓取', workflow_id: 'jd', modes: ['fast'] }],
    }));
    return;
  }
  if (request.method === 'POST' && request.url === '/v1/workflows/run') {
    runCount += 1;
    const parsed = JSON.parse(Buffer.concat(body).toString('utf8'));
    response.writeHead(202, { 'content-type': 'application/json' });
    response.end(JSON.stringify({
      ok: true,
      state: 'accepted',
      workflow: parsed.workflow,
      request_id: parsed.request_id,
    }));
    return;
  }
  response.writeHead(404, { 'content-type': 'application/json' });
  response.end(JSON.stringify({ ok: false, error: 'not_found' }));
});

await new Promise(resolveListen => bridge.listen(0, '127.0.0.1', resolveListen));
const port = bridge.address().port;
await writeFile(join(temporary, 'config.json'), JSON.stringify({
  bridgeUrl: `http://127.0.0.1:${port}`,
  bridgeToken: token,
  allowedOpenIds: ['ou_owner'],
}));

const child = spawn(process.execPath, [resolve('src/mcp/server.js')], {
  cwd: resolve('.'),
  env: { ...process.env, BOTMUX_PLUGIN_HOME: temporary },
  stdio: ['pipe', 'pipe', 'inherit'],
});
const lines = readline.createInterface({ input: child.stdout, crlfDelay: Infinity });
const pending = new Map();
lines.on('line', line => {
  const message = JSON.parse(line);
  const waiter = pending.get(message.id);
  if (waiter) {
    pending.delete(message.id);
    waiter(message);
  }
});

function request(id, method, params = {}) {
  return new Promise((resolveRequest, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`MCP request ${id} timed out`));
    }, 5_000);
    pending.set(id, message => {
      clearTimeout(timer);
      resolveRequest(message);
    });
    child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
  });
}

try {
  const initialized = await request(1, 'initialize', { protocolVersion: '2024-11-05' });
  if (initialized.result?.serverInfo?.name !== 'seele-rpa') throw new Error('initialize failed');

  const listed = await request(2, 'tools/call', {
    name: 'seele_list_workflows',
    arguments: {},
  });
  if (listed.result?.isError) throw new Error('workflow listing failed');

  const denied = await request(3, 'tools/call', {
    name: 'seele_run_workflow',
    arguments: { workflow: '京东数据抓取', request_id: 'denied' },
  });
  if (!denied.result?.isError || runCount !== 0) throw new Error('missing trusted caller was not denied');

  const accepted = await request(4, 'tools/call', {
    name: 'seele_run_workflow',
    arguments: { workflow: '京东数据抓取', request_id: 'accepted' },
    _meta: { botmuxTrustedCaller: { requestUserOpenId: 'ou_owner' } },
  });
  if (accepted.result?.isError || runCount !== 1) throw new Error('trusted workflow run failed');
  console.log('Seele MCP smoke test passed.');
} finally {
  child.kill();
  lines.close();
  await new Promise(resolveClose => bridge.close(resolveClose));
  await rm(temporary, { recursive: true, force: true });
}
