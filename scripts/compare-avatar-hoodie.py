"""Compare actual hoodie renders and independently verify the locked parts."""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'artwork/avatar'
OUT = ART/'validation'
previous, current = sys.argv[1:3] or ('v9', 'v10')
font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
font = ImageFont.truetype(font_path, 23)
small = ImageFont.truetype(font_path, 18)

# Preserve the original camera framing. Crop only to enlarge the clothing in
# the comparison; do not warp or retouch the reference or rendered pixels.
sheet = Image.new('RGB', (1458, 1048), 'white')
draw = ImageDraw.Draw(sheet)
for i, label in enumerate(('Reference', f'{previous.upper()} · saved', f'{current.upper()} · refined hoodie')):
    draw.text((16+i*486, 15), label, font=font, fill='#222222')
for row, (view, label) in enumerate((('three-quarter','Front'),('side','Side'),('rear','Rear'))):
    top = 56+row*330
    draw.line((16, top, 1442, top), fill='#dddddd')
    draw.text((16, top+8), label, font=small, fill='#555555')
    paths = [ART/'reference-inputs'/f'{view}.png',
             OUT/f'{previous}-calibrated/{view}.png',
             OUT/f'{current}-calibrated/{view}.png']
    for column, path in enumerate(paths):
        im = Image.open(path).convert('RGB')
        assert im.height == 740
        crop = im.crop((0, 450, im.width, 740))
        sheet.paste(crop, (column*486+(486-im.width)//2, top+34))
sheet.save(OUT/f'hoodie-details-{previous}-{current}.png')

sheet = Image.new('RGB', (1128, 936), 'white')
draw = ImageDraw.Draw(sheet)
for i, angle in enumerate(range(0, 360, 45)):
    x, y = (i%4)*282, (i//4)*468
    im = Image.open(OUT/f'{current}-calibrated/orbit-{angle:03d}.png').convert('RGB')
    sheet.paste(im.resize((282, 444), Image.Resampling.LANCZOS), (x,y+24))
    draw.text((x+12,y+3), f'{angle}°', font=small, fill='#292929')
sheet.save(OUT/f'rotation-{current}.png')

# Compare both rear shoulder transitions directly, not just the reference views.
sheet=Image.new('RGB',(1024,1048),'white');draw=ImageDraw.Draw(sheet)
for i,label in enumerate((f'{previous.upper()} · saved',f'{current.upper()} · refined shoulders')):
    draw.text((16+i*512,15),label,font=font,fill='#222222')
for row,(view,label) in enumerate((('three-quarter','Front'),('orbit-120','Rear shoulder · 120°'),('orbit-240','Opposite rear shoulder · 240°'))):
    top=56+row*330
    draw.line((16,top,1008,top),fill='#dddddd');draw.text((16,top+8),label,font=small,fill='#555555')
    for column,version in enumerate((previous,current)):
        im=Image.open(OUT/f'{version}-calibrated/{view}.png').convert('RGB')
        sheet.paste(im.crop((0,450,im.width,740)),(column*512+(512-im.width)//2,top+34))
sheet.save(OUT/f'shoulder-details-{previous}-{current}.png')

if (OUT/f'{current}-clothing').is_dir():
    for section,angles in [('front',list(range(0,90,15))+list(range(270,360,15))),('rear',list(range(90,270,15)))]:
        sheet=Image.new('RGB',(1536,1552),'white');draw=ImageDraw.Draw(sheet)
        for i,angle in enumerate(angles):
            x=(i%3)*512;y=(i//3)*388
            im=Image.open(OUT/f'{current}-clothing/orbit-{angle:03d}.png').convert('RGB')
            sheet.paste(im,(x,y+28));draw.text((x+14,y+3),f'{angle}°',font=small,fill='#333333')
        sheet.save(OUT/f'clothing-{section}-{current}.png')

meshes = [np.load(OUT/f'{v}-calibrated/geometry.npz') for v in (previous,current)]
parts = [json.loads((OUT/f'{v}-calibrated/parts.json').read_text()) for v in (previous,current)]
refinement = json.loads((OUT/f'refinement-{current}.json').read_text())
locked = refinement['lockedParts']
report = {'previous':previous,'current':current,'lockedParts':{},'unchanged':True}
for name in locked:
    geometry=[]
    for data, lookup in zip(meshes,parts):
        start,end = lookup[name]
        faces = data['triangles']
        local = faces[np.all((faces >= start)&(faces < end),axis=1)]-start
        geometry.append((data['vertices'][start:end],local))
    vertices_equal = np.array_equal(geometry[0][0], geometry[1][0])
    faces_equal = np.array_equal(geometry[0][1], geometry[1][1])
    assert vertices_equal and faces_equal, f'Locked geometry changed: {name}'
    report['lockedParts'][name] = {'vertices':len(geometry[0][0]),'verticesIdentical':vertices_equal,'facesIdentical':faces_equal}
(OUT/f'preservation-{current}.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(locked)} locked parts match {previous} exactly, including the entire accepted head.')
