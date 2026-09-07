import type { ImageMetadata } from 'astro';

const assets = import.meta.glob<{ default: ImageMetadata }>('../assets/**/*.{png,jpg,jpeg,webp}', { eager: true });

export function imageAsset(path: string): ImageMetadata {
  const image = assets[`../assets/${path}`]?.default;
  if (!image) throw new Error(`Missing image asset: ${path}`);
  return image;
}

export function galleryFileName(path: string): string {
  const name = path.split('/').at(-1);
  if (!name) throw new Error(`Invalid gallery path: ${path}`);
  return name;
}

export const galleryImage = (path: string) => imageAsset(`gallery/${galleryFileName(path)}`);
export const galleryPreview = (path: string) => isAnimatedGalleryImage(path)
  ? imageAsset(`previews/${galleryFileName(path)}`)
  : galleryImage(path);
export const galleryVideoSrc = (path: string) => `/videos/gallery/${galleryFileName(path).replace('.webp', '.mp4')}`;

// Animated exports use still previews for cards and MP4 playback in project viewers.
export const animatedGalleryImages = new Set(['BEAN25_2.webp', 'BEAN26_2.webp', 'clampcase_2.webp', 'poopchute_2.webp']);
export const isAnimatedGalleryImage = (path: string) => animatedGalleryImages.has(galleryFileName(path));
