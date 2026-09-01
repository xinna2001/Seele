import { cp, mkdir, rm } from 'node:fs/promises';

await rm(new URL('../dist/', import.meta.url), { recursive: true, force: true });
await mkdir(new URL('../dist/skills/seele-rpa/', import.meta.url), { recursive: true });
await mkdir(new URL('../dist/mcp/', import.meta.url), { recursive: true });
await cp(
  new URL('../skills/seele-rpa/SKILL.md', import.meta.url),
  new URL('../dist/skills/seele-rpa/SKILL.md', import.meta.url),
);
await cp(
  new URL('../src/mcp/index.json', import.meta.url),
  new URL('../dist/mcp/index.json', import.meta.url),
);
await cp(
  new URL('../src/mcp/server.js', import.meta.url),
  new URL('../dist/mcp/server.js', import.meta.url),
);
