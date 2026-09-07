# michaelsite-v4

## Git identity

- Keep changes local. Do not commit or push unless the user explicitly requests it for those changes.

- All commits and pushes must use `michael-aguilar-web`, never `michael-aguilar`.
- Author and committer: `michael-aguilar-web <michael.b.aguilar+web@gmail.com>`.
- Run `npm run setup:git` on a fresh checkout. This installs repository-local identity settings and tracked hooks.
- Verify `npm run check:identity` before committing and `npm run check:github` before pushing. Never bypass the hooks, override the identity, or silently use the main account.
- Keep changes to Git configuration local to this repository.

## Development

- Do not use computer/browser UI automation for verification unless the user explicitly requests it. Use builds and relevant code checks; the user handles visual review.

- Follow broccosite-v4's Astro + MDX content-collection architecture.
- Use `npm run dev -- --background` for a background preview; manage it with `npm run astro -- dev status`, `dev logs`, and `dev stop`.
- Run `npm run build` and `npm run check:site` before delivery.
- Keep article content in `src/data/wiki`, gallery data in `src/data/gallery.json`, and branding separate from wiki navigation.
- Preserve existing public URLs through redirects when changing routes.
- GitHub Pages deploys automatically after checks on pushes to main, matching broccosite-v4. The custom-domain cutover is a separate step; leave v3 serving the domain until that transfer is requested.

## UI copy

- Prefer concise, functional interface copy. Do not add marketing taglines, decorative headings, redundant descriptions, or explanatory subtext unless requested or necessary to understand an action, state, risk, or error.
- Preserve Poppins and Outfit and the professional site's red accent palette.
