import { access, readFile } from 'node:fs/promises';

const required = [
  '../dist/skills/seele-rpa/SKILL.md',
  '../dist/mcp/index.json',
  '../dist/mcp/server.js',
];

for (const relative of required) {
  await access(new URL(relative, import.meta.url));
}

const skill = await readFile(new URL('../dist/skills/seele-rpa/SKILL.md', import.meta.url), 'utf8');
if (!skill.startsWith('---\n') || !skill.includes('name: "seele-rpa"')) {
  throw new Error('invalid Seele skill frontmatter');
}

const mcp = JSON.parse(await readFile(new URL('../dist/mcp/index.json', import.meta.url), 'utf8'));
if (mcp.transport !== 'stdio' || !Array.isArray(mcp.command)) {
  throw new Error('invalid MCP manifest');
}

console.log('Seele Botmux plugin is valid.');
