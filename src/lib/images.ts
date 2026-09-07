import type { ImageMetadata } from 'astro';

const assets = import.meta.glob<{ default: ImageMetadata }>('../assets/**/*.{png,jpg,jpeg,webp}', { eager: true });

export function imageAsset(path: string): ImageMetadata {
  const image = assets[`../assets/${path}`]?.default;
  if (!image) throw new Error(`Missing image asset: ${path}`);
  return image;
}

export const galleryImage = (path: string) => imageAsset(`gallery/${path.split('/').at(-1)}`);
export const galleryPreview = (path: string) => isAnimatedGalleryImage(path)
  ? imageAsset(`previews/${path.split('/').at(-1)}`)
  : galleryImage(path);

// Keep the original animated CAD exports intact in project viewers.
export const animatedGalleryImages = new Set(['BEAN25_2.webp', 'BEAN26_2.webp', 'clampcase_2.webp', 'poopchute_2.webp']);
export const isAnimatedGalleryImage = (path: string) => animatedGalleryImages.has(path.split('/').at(-1)!);
