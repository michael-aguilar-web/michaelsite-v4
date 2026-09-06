import { execFileSync } from 'node:child_process';

export const webName = 'michael-aguilar-web';
export const webEmail = 'michael.b.aguilar+web@gmail.com';
export function checkIdentity() {
  for (const role of ['AUTHOR', 'COMMITTER']) {
    const identity = execFileSync('git', ['var', `GIT_${role}_IDENT`], { encoding: 'utf8' }).trim();
    if (!identity.startsWith(`${webName} <${webEmail}> `)) {
      throw new Error(`${role.toLowerCase()} must be ${webName} <${webEmail}>. Run npm run setup:git and remove any conflicting GIT_AUTHOR_* or GIT_COMMITTER_* overrides.`);
    }
  }
}
try {
  checkIdentity();
  console.log(`Commit identity verified: ${webName} <${webEmail}>`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
