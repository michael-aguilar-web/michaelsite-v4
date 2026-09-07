import { readFile, readdir } from 'node:fs/promises';
import { resolve, join, relative } from 'node:path';
import assert from 'node:assert/strict';

const output = resolve('dist');
const errors = [];
async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  return (await Promise.all(entries.map((entry) => entry.isDirectory() ? walk(join(dir, entry.name)) : join(dir, entry.name)))).flat();
}
const files = await walk(output);
const paths = new Set(files);
const htmlFiles = files.filter((file) => file.endsWith('.html'));
const pages = new Map(await Promise.all(htmlFiles.map(async (file) => [file, await readFile(file, 'utf8')])));
const origin = 'https://michaelbaguilar.com';

for (const [file, html] of pages) {
  const sourcePath = '/' + relative(output, file).replace(/index\.html$/, '');
  if (!html.includes('http-equiv="refresh"')) {
    if (!/<html[^>]*lang="en"/.test(html)) errors.push(`${sourcePath}: missing document language`);
    if (!/name="viewport"/.test(html)) errors.push(`${sourcePath}: missing mobile viewport`);
    if ((html.match(/<h1(?:\s|>)/g) || []).length !== 1) errors.push(`${sourcePath}: expected one primary heading`);
  }
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
  if (ids.length !== new Set(ids).size) errors.push(`${sourcePath}: duplicate element IDs`);
  for (const match of html.matchAll(/<(?:a|img|video|script|link|iframe)\b[^>]*\b(?:href|src)="([^"]+)"/g)) {
    const raw = match[1].replaceAll('&amp;', '&');
    if (!raw || /^(?:mailto:|tel:|data:|javascript:)/.test(raw)) continue;
    const url = new URL(raw, new URL(sourcePath, origin));
    if (url.origin !== origin) continue;
    const pathname = decodeURIComponent(url.pathname);
    const target = resolve(output, '.' + pathname);
    const destination = paths.has(target) ? target : join(target, 'index.html');
    if (!paths.has(destination)) { errors.push(`${sourcePath}: missing target ${raw}`); continue; }
    if (url.hash && pages.has(destination)) {
      const id = decodeURIComponent(url.hash.slice(1));
      if (id && !pages.get(destination).includes(`id="${id}"`)) errors.push(`${sourcePath}: missing anchor ${raw}`);
    }
  }
  for (const match of html.matchAll(/<img\b[^>]*>/g)) {
    if (!/\salt(?:=|\s|\/?>)/.test(match[0])) errors.push(`${sourcePath}: image without alternative text`);
    const imageSrc = match[0].match(/\bsrc="([^"]+)"/)?.[1];
    const preservedAnimation = /\/(?:BEAN25_2|BEAN26_2|clampcase_2|poopchute_2)\.webp$/.test(imageSrc || '');
    if (imageSrc?.startsWith('/') && !imageSrc.startsWith('/_astro/') && !preservedAnimation) {
      errors.push(`${sourcePath}: local static image bypasses Astro optimization: ${imageSrc}`);
    }
    for (const candidate of (match[0].match(/\bsrcset="([^"]+)"/)?.[1] || '').split(',')) {
      const url = candidate.trim().split(/\s+/)[0];
      if (url?.startsWith('/') && !paths.has(resolve(output, '.' + url))) errors.push(`${sourcePath}: missing responsive image ${url}`);
    }
  }
  if (sourcePath.startsWith('/wiki/') && !html.includes('http-equiv="refresh"')) {
    if (!html.includes('name="robots" content="noindex, nofollow"')) errors.push(`${sourcePath}: hidden wiki should not be indexed`);
    if (html.includes('[[')) errors.push(`${sourcePath}: unconverted Emanote link`);
  } else if (!html.includes('http-equiv="refresh"')) {
    const nav = html.match(/<nav aria-label="Main navigation"[\s\S]*?<\/nav>/)?.[0] || '';
    if (nav.includes('/wiki/')) errors.push(`${sourcePath}: wiki is exposed in main navigation`);
  }
}

const gallery = JSON.parse(await readFile('src/data/gallery.json', 'utf8'));
assert.equal(gallery.reduce((sum, category) => sum + category.projects.length, 0), 14, 'All v3 projects should be present');
for (const category of gallery) {
  const html = pages.get(join(output, 'gallery', category.id, 'index.html'));
  for (const project of category.projects) {
    assert.ok(html?.includes(`id="${project.id}"`), `Missing gallery project: ${project.title}`);
    for (const image of project.images) {
      assert.ok(paths.has(resolve(output, '.' + image)), `Missing original image: ${image}`);
      if (/\/(BEAN25_2|BEAN26_2|clampcase_2|poopchute_2)\.webp$/.test(image)) {
        const video = '/videos/gallery/' + image.split('/').at(-1).replace('.webp', '.mp4');
        assert.ok(paths.has(resolve(output, '.' + video)), `Missing gallery animation: ${video}`);
        assert.ok(html.includes(video), `Animation is not used by its project: ${video}`);
      }
    }
    for (const link of project.links) assert.ok(html.includes(link.url.replaceAll('&', '&amp;')), `Missing project link: ${link.url}`);
  }
}
const expectedNotes = ['golden-rules', 'design-general', 'notable-matches', 'mechanisms/bumpers', 'mechanisms/climbers', 'mechanisms/elevators', 'mechanisms/hoppers-serializers-indexers', 'mechanisms/intakes'];
for (const slug of expectedNotes) assert.ok(pages.has(join(output, 'wiki', slug, 'index.html')), `Missing original wiki URL: ${slug}`);
for (const slug of ['gallery-frc', 'gallery-3dp', 'gallery-apps']) assert.ok(pages.get(join(output, slug, 'index.html'))?.includes('http-equiv="refresh"'), `Missing legacy gallery redirect: ${slug}`);
const home = pages.get(join(output, 'index.html'));
assert.ok(pages.get(join(output, 'wiki/mechanisms/index.html'))?.includes('http-equiv="refresh"'), 'The retired mechanisms overview should redirect');
assert.match(home, /id="wiki-link" hidden/, 'Homepage wiki entry should remain hidden');
if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log(`Checked ${htmlFiles.length} HTML pages: internal links, anchors, image files, hidden wiki, 14 projects, and ${expectedNotes.length} wiki articles.`);
