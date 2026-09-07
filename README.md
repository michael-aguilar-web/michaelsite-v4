# michaelsite-v4

Michael Aguilar’s professional site, migrated from Emanote to the Astro + MDX architecture used by broccosite-v4. Production domain: `michaelbaguilar.com`.

## Git account — required on every checkout

All authors, committers, and pushes must use **michael-aguilar-web**, never michael-aguilar.

```sh
npm run setup:git
npm run check:identity
npm run check:github
```

`setup:git` applies repository-local settings (not global settings):

- Name: `michael-aguilar-web`
- Email: `michael.b.aguilar+web@gmail.com`
- Tracked hooks: `.githooks`
- HTTPS credentials scoped to the web account and this repository

The pre-commit hook rejects a mismatched author or committer. The pre-push hook checks outgoing commits, restricts the destination to `https://github.com/michael-aguilar-web/michaelsite-v4.git`, and checks the credential’s actual GitHub account through `/user`. Credentials are handled in memory and are never printed. Sign into the web account in your Git credential manager before pushing. Do not disable these hooks or use `--no-verify`.

## Develop

Requires Node.js 22.12+.

```sh
npm ci
npm run dev -- --background
npm run astro -- dev status
npm run astro -- dev logs
npm run astro -- dev stop
```

The dev command prints its local URL. For a foreground server, use `npm run dev`.

```sh
npm run build
npm run check:site
```

## Content and structure

- `src/pages/index.astro`: homepage and hidden wiki entry. Hold the portrait for 800 ms with a mouse or touch; keyboard activation also reveals it.
- `src/data/gallery.json`: original project titles, photos, detail HTML, and links. Categories and project cards render from these records.
- `src/assets/gallery` and `src/assets/branding`: imported source images for Astro's `Image` / `getImage()` pipeline. Gallery cards and slideshows use responsive WebP variants; static modal images use WebP at up to 1920 pixels wide.
- `src/assets/previews`: still frames for animated gallery exports. Register new animations in `src/lib/images.ts` so their modal playback stays intact. Original animated files load only when selected.
- `public/images/gallery`: original media retained at existing URLs for compatibility. Existing `public/images/previews` URLs are also preserved; the UI now uses Astro-generated variants.
- Externally hosted wiki images and the dynamic article lightbox keep the same plain-image fallback used by broccosite.
- `src/data/wiki`: Markdown / MDX articles. Folder paths become `/wiki/` URLs and navigation branches automatically.
- `src/content.config.ts`: wiki schema, consistent with broccosite-v4 (`title`, `description`, `order`, `draft`, `publishedDate`, `updatedDate`).
- `src/lib/wiki.ts`: content-independent navigation tree builder.
- `src/components/WikiLayout.astro` and `WikiTree.astro`: wiki shell and nested navigation.
- `src/styles/global.css`: site palette, Poppins / Outfit typography, and site layout.
- `src/styles/wiki.css` and `content.css`: wiki and article styling.

To add a wiki article, create a file such as `src/data/wiki/mechanisms/example.mdx`:

```md
---
title: example
order: 20
draft: false
---

## Notes

Article content goes here.
```

The title comes from frontmatter, so start article headings at `##`. Use regular links such as `[intakes](/wiki/mechanisms/intakes/)`. Use `draft: true` to omit a note from both routes and navigation. A parent article such as `mechanisms.mdx` becomes the folder’s Overview link.

The wiki stays outside public navigation. Wiki pages include `noindex, nofollow`; direct URLs remain accessible. `src/lib/site.ts` holds the navigation visibility setting. This is discoverability control, not access control.

## Deployment

GitHub Actions builds and checks pushes and pull requests using the same Pages action family as broccosite-v4. Pushes to `main` and manual workflow runs deploy after the build and site checks pass. Pull requests only build and check.

GitHub Pages uses GitHub Actions. The custom domain remains on v3 until the separate domain transfer. The build targets the domain root, so the temporary GitHub project URL is not a complete browsing preview before cutover. Transfer the custom domain from v3 to v4 after verifying deployment; existing root-relative URLs then work on michaelbaguilar.com.

## Migration record

- Emanote source: `michael-aguilar-web/michaelsite-v3` at `b137d0271356504469828c2d59e7db28543596ab`.
- Astro reference: `broccosite-v4` at `684206d0b7301cf20a7bda946b728072a51472dc`.
- Migrated all 14 gallery projects and 9 wiki articles, retaining project links and original media.
- The mechanisms overview has been retired; its old URL redirects to `/wiki/`, and its five articles remain in the sidebar folder. Preserved the other 8 wiki URLs. Old `/gallery-frc`, `/gallery-3dp`, and `/gallery-apps` URLs redirect to the category routes.
- Converted Emanote wikilinks to normal links and image width annotations to HTML image widths.
- Replaced the mechanisms index’s `asdfasdf` placeholder and incomplete contents list with links to all existing mechanism notes. Other article wording remains intact.
- Original externally hosted wiki images remain externally hosted.
- Wiki behavior is adapted locally from broccosite. A shared package has not yet been extracted; `src/lib/wiki.ts` and the wiki components provide the extraction boundary.
