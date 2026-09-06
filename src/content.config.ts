import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const wiki = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/data/wiki' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    draft: z.boolean().default(false),
    publishedDate: z.coerce.date().optional(),
    updatedDate: z.coerce.date().optional(),
    order: z.number().default(10),
  }),
});
export const collections = { wiki };
