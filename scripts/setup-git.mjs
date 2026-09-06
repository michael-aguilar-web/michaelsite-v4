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
for (const hook of ['pre-commit', 'pre-push']) chmodSync(`.githooks/${hook}`, 0o755);
console.log('Repository-local web-account identity and Git hooks configured.');
