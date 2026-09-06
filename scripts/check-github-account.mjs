import { spawnSync } from 'node:child_process';

// Credentials stay in memory and are never printed or written to the repository.
const credential = spawnSync('git', ['credential', 'fill'], {
  input: 'protocol=https\nhost=github.com\npath=michael-aguilar-web/michaelsite-v4.git\nusername=michael-aguilar-web\n\n',
  encoding: 'utf8',
  env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_ASKPASS: '/usr/bin/false' },
  timeout: 15000,
});
const fields = Object.fromEntries((credential.stdout || '').trim().split('\n').map((line) => {
  const equals = line.indexOf('=');
  return [line.slice(0, equals), line.slice(equals + 1)];
}));
try {
  if (credential.status !== 0 || !fields.password) throw new Error('No HTTPS credential is available for michael-aguilar-web. Sign in with the web account before pushing.');
  const response = await fetch('https://api.github.com/user', {
    headers: { Authorization: `Bearer ${fields.password}`, Accept: 'application/vnd.github+json', 'User-Agent': 'michaelsite-v4-account-check' },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error('GitHub could not verify the stored web-account credential.');
  const { login } = await response.json();
  if (login !== 'michael-aguilar-web') throw new Error(`Push blocked: the credential belongs to ${login}, not michael-aguilar-web.`);
  console.log('GitHub authentication verified: michael-aguilar-web');
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
