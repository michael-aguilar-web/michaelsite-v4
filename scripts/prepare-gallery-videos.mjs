// Run with Node.js and FFmpeg installed. Original animated WebPs remain unchanged.
import sharp from 'sharp';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, stat } from 'node:fs/promises';
const names = ['BEAN25_2', 'BEAN26_2', 'clampcase_2', 'poopchute_2'];
await mkdir('public/videos/gallery', { recursive: true });
for (const name of names) {
  const input = `public/images/gallery/${name}.webp`;
  const output = `public/videos/gallery/${name}.mp4`;
  const metadata = await sharp(input).metadata();
  const duration = metadata.delay.reduce((sum, delay) => sum + delay, 0);
  // These source animations use alternating 66/67ms delays (~15fps).
  if (metadata.delay.some(delay => Math.abs(delay - duration / metadata.pages) > 1)) throw new Error(`Variable timing needs separate handling: ${name}`);
  const first = await sharp(input, { page: 0, pages: 1 }).flatten({ background: '#fff' }).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const encoder = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', `${first.info.width}x${first.info.height}`, '-framerate', `${metadata.pages * 1000}/${duration}`, '-i', 'pipe:0', '-an', '-vf', 'scale=720:-2', '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = once(encoder, 'close');
  for (let page = 0; page < metadata.pages; page += 32) {
    const count = Math.min(32, metadata.pages - page);
    const frames = await sharp(input, { page, pages: count }).flatten({ background: '#fff' }).removeAlpha().raw().toBuffer();
    if (!encoder.stdin.write(frames)) await once(encoder.stdin, 'drain');
    console.log(`${name}: encoded ${page + count}/${metadata.pages} frames`);
  }
  encoder.stdin.end();
  const [code] = await done;
  if (code !== 0) throw new Error(`FFmpeg failed for ${name}`);
  console.log(`${name}: ${(await stat(input)).size} → ${(await stat(output)).size} bytes; ${metadata.pages} frames / ${duration}ms`);
}
