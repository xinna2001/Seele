import readline from 'node:readline';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function loadPluginConfig() {
  const pluginHome = process.env.BOTMUX_PLUGIN_HOME || '';
  if (!pluginHome) return {};
  try {
    const parsed = JSON.parse(readFileSync(join(pluginHome, 'config.json'), 'utf8'));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

const pluginConfig = loadPluginConfig();
const bridgeUrl = String(
  process.env.SEELE_BRIDGE_URL
  || pluginConfig.bridgeUrl
  || 'http://127.0.0.1:8765',
).replace(/\/+$/, '');
const bridgeToken = String(process.env.SEELE_BRIDGE_TOKEN || pluginConfig.bridgeToken || '');
const configuredOpenIds = process.env.SEELE_ALLOWED_OPEN_IDS || pluginConfig.allowedOpenIds || '';
const allowedOpenIds = new Set(
  (Array.isArray(configuredOpenIds) ? configuredOpenIds : String(configuredOpenIds).split(','))
    .flatMap(value => String(value).split(','))
    .map(value => value.trim())
    .filter(Boolean),
);

const tools = [
  {
    name: 'seele_list_workflows',
    description: 'List the allowlisted Seele/Yingdao workflows available on the desktop.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'seele_run_workflow',
    description: 'Run one allowlisted Seele/Yingdao workflow by display name or workflow ID.',
    inputSchema: {
      type: 'object',
      properties: {
        workflow: {
          type: 'string',
          description: 'Exact workflow display name or allowlisted workflow ID.',
        },
        request_id: {
          type: 'string',
          description: 'Stable idempotency key. Omit to generate one.',
        },
        startup_mode: {
          type: 'string',
          enum: ['slow', 'fast'],
          description: 'Optional Seele dispatch mode override.',
        },
      },
      required: ['workflow'],
      additionalProperties: false,
    },
  },
  {
    name: 'seele_workflow_status',
    description: 'Read the latest known state of a previously submitted Seele workflow.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string' },
      },
      required: ['request_id'],
      additionalProperties: false,
    },
  },
];

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function resultText(value, isError = false) {
  return {
    content: [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    isError,
  };
}

function trustedCaller(params) {
  const caller = params?._meta?.botmuxTrustedCaller;
  return caller && typeof caller === 'object' ? caller : null;
}

function assertAuthorizedCaller(params) {
  const caller = trustedCaller(params);
  const openId = String(caller?.requestUserOpenId || '');
  if (!openId) {
    throw new Error('A trusted Botmux/Lark caller identity is required.');
  }
  if (allowedOpenIds.size > 0 && !allowedOpenIds.has(openId)) {
    throw new Error('This Lark user is not allowed to run Seele workflows.');
  }
}

async function bridgeRequest(path, options = {}) {
  const headers = {
    accept: 'application/json',
    ...(options.body ? { 'content-type': 'application/json' } : {}),
    ...(bridgeToken ? { authorization: `Bearer ${bridgeToken}` } : {}),
  };
  const response = await fetch(`${bridgeUrl}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
    signal: AbortSignal.timeout(15_000),
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`Seele bridge returned non-JSON HTTP ${response.status}.`);
  }
  if (!response.ok) {
    throw new Error(body.detail || body.message || body.error || `Seele bridge HTTP ${response.status}`);
  }
  return body;
}

async function callTool(params) {
  const args = params.arguments || {};
  switch (params.name) {
    case 'seele_list_workflows':
      return resultText(await bridgeRequest('/v1/workflows'));
    case 'seele_run_workflow': {
      assertAuthorizedCaller(params);
      const requestId = String(args.request_id || `botmux-${randomUUID()}`);
      return resultText(await bridgeRequest('/v1/workflows/run', {
        method: 'POST',
        body: JSON.stringify({
          workflow: String(args.workflow || ''),
          request_id: requestId,
          ...(args.startup_mode ? { startup_mode: args.startup_mode } : {}),
        }),
      }));
    }
    case 'seele_workflow_status': {
      assertAuthorizedCaller(params);
      const requestId = encodeURIComponent(String(args.request_id || ''));
      return resultText(await bridgeRequest(`/v1/jobs/${requestId}`));
    }
    default:
      throw new Error(`Unknown tool: ${params.name}`);
  }
}

async function handle(message) {
  if (!message || message.jsonrpc !== '2.0' || message.id === undefined) {
    return;
  }
  try {
    let result;
    switch (message.method) {
      case 'initialize':
        result = {
          protocolVersion: message.params?.protocolVersion || '2024-11-05',
          capabilities: { tools: {} },
          serverInfo: { name: 'seele-rpa', version: '0.1.0' },
        };
        break;
      case 'ping':
        result = {};
        break;
      case 'tools/list':
        result = { tools };
        break;
      case 'tools/call':
        result = await callTool(message.params || {});
        break;
      default:
        send({
          jsonrpc: '2.0',
          id: message.id,
          error: { code: -32601, message: `Method not found: ${message.method}` },
        });
        return;
    }
    send({ jsonrpc: '2.0', id: message.id, result });
  } catch (error) {
    send({
      jsonrpc: '2.0',
      id: message.id,
      result: resultText({ ok: false, error: String(error?.message || error) }, true),
    });
  }
}

const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
input.on('line', line => {
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    return;
  }
  void handle(message);
});
