import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

// Git consumes this helper's output directly. Never log or persist the token.
if (process.argv[2] !== 'get') process.exit(0);
const request = Object.fromEntries(readFileSync(0, 'utf8').trim().split('\n').map((line) => {
  const equals = line.indexOf('=');
  return [line.slice(0, equals), line.slice(equals + 1)];
}));
const account = 'michael-aguilar-web';
if (request.protocol !== 'https' || request.host !== 'github.com'
    || !/^michael-aguilar-web\/michaelsite-v4(?:\.git)?$/.test(request.path ?? '')
    || (request.username && request.username !== account)) process.exit(0);

// Select the named keyring account even when another account is active in gh.
const env = { ...process.env };
for (const name of ['GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN']) delete env[name];
const result = spawnSync('gh', ['auth', 'token', '--hostname', 'github.com', '--user', account], {
  encoding: 'utf8', env, timeout: 15000,
});
const token = result.stdout?.trim();
if (result.status !== 0 || !token || /[\r\n]/.test(token)) process.exit(1);
process.stdout.write(`username=${account}\npassword=${token}\n\n`);
