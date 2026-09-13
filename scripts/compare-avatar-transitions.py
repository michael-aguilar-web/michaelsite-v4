"""Compare the front and ear transitions using saved, actual Blender renders."""
from pathlib import Path
import argparse, importlib.util, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artwork/avatar/validation'
parser=argparse.ArgumentParser()
parser.add_argument('previous',nargs='?',default='v7')
parser.add_argument('current',nargs='?',default='v8')
parser.add_argument('--hair',action='store_true')
args=parser.parse_args();previous,current=args.previous,args.current
font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
font = ImageFont.truetype(font_path, 22)
small = ImageFont.truetype(font_path, 18)

sheet = Image.new('RGB', (1032, 1724), 'white')
draw = ImageDraw.Draw(sheet)
draw.text((32, 24), f'{previous.upper()} · saved version', font=font, fill='#292929')
heading='sculpted hair' if args.hair else 'refined sides and nape'
draw.text((548, 24), f'{current.upper()} · {heading}', font=font, fill='#292929')
views=([('three-quarter','Approved front view'),('orbit-270','Left side'),('orbit-180','Back')]
       if args.hair else [('three-quarter','Approved front view'),('orbit-240','Behind the left ear'),('orbit-120','Behind the right ear')])
for i, (name, title) in enumerate(views):
    y = 80+i*548
    draw.line((24, y, 1008, y), fill='#dddddd')
    draw.text((32, y+12), title, font=small, fill='#555555')
    for x, version in [(24, previous), (540, current)]:
        im = Image.open(OUT/f'{version}-calibrated/{name}.png').convert('RGB')
        assert im.size == (470, 740)
        sheet.paste(im.crop((0, 0, 470, 500)), (x, y+40))
prefix='hair-details' if args.hair else 'ear-transitions'
sheet.save(OUT/f'{prefix}-{previous}-{current}.png')

sheet = Image.new('RGB', (1128, 936), 'white')
draw = ImageDraw.Draw(sheet)
for i, angle in enumerate(range(0, 360, 45)):
    x, y = (i % 4)*282, (i//4)*468
    im = Image.open(OUT/f'{current}-calibrated/orbit-{angle:03d}.png').convert('RGB')
    sheet.paste(im.resize((282, 444), Image.Resampling.LANCZOS), (x, y+24))
    draw.text((x+12, y+3), f'{angle}°', font=small, fill='#292929')
sheet.save(OUT/f'rotation-{current}.png')

spec = importlib.util.spec_from_file_location('fit', ROOT/'scripts/fit-avatar-silhouettes.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
data = [np.load(OUT/f'{version}-calibrated/geometry.npz') for version in (previous, current)]
report = {}
for yaw in (0, 17):
    masks = [fit.raster(d['vertices'], 'three-quarter', [yaw, 6, .998, -9, -12], 1,
                       np.ascontiguousarray(d['triangles'], np.int32),
                       np.ascontiguousarray(d['labels'], np.uint8)) for d in data]
    report[str(yaw)] = {'differentPixels': int((masks[0] != masks[1]).sum()),
                        'foregroundPixels': int((masks[0] != 0).sum()),
                        'hairDifferencePixels': int(((masks[0] == 1) != (masks[1] == 1)).sum()),
                        'overlap': fit.overlap(*masks).tolist()}
(OUT/f'front-preservation-{current}.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
