import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://michaelbaguilar.com',
  trailingSlash: 'always',
  integrations: [mdx()],
  redirects: {
    '/index': '/',
    '/gallery-frc': '/gallery/frc/',
    '/gallery-3dp': '/gallery/3d-prints/',
    '/gallery-apps': '/gallery/apps/',
  },
});
