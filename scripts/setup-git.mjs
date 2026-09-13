import { execFileSync } from 'node:child_process';
import { chmodSync } from 'node:fs';

const settings = {
  'user.name': 'michael-aguilar-web',
  'user.email': 'michael.b.aguilar+web@gmail.com',
  'user.useConfigOnly': 'true',
  'core.hooksPath': '.githooks',
  'credential.https://github.com.username': 'michael-aguilar-web',
  'credential.https://github.com.useHttpPath': 'true',
};
for (const [key, value] of Object.entries(settings)) {
  execFileSync('git', ['config', '--local', key, value]);
}
// Clear inherited helpers and select the web account without switching gh's
// active account for other repositories.
execFileSync('git', ['config', '--local', '--replace-all', 'credential.https://github.com.helper', '']);
execFileSync('git', ['config', '--local', '--add', 'credential.https://github.com.helper', '!node scripts/github-web-credential.mjs']);
for (const hook of ['pre-commit', 'pre-push']) chmodSync(`.githooks/${hook}`, 0o755);
console.log('Repository-local web-account identity and Git hooks configured.');
