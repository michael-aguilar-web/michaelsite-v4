"""Create side-by-side evidence from actual Blender renders and mesh masks."""
from pathlib import Path
import importlib.util, json, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
spec=importlib.util.spec_from_file_location('fit_avatar',ROOT/'scripts/fit-avatar-silhouettes.py')
fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
cameras=json.loads((ART/'validation/calibrated-cameras.json').read_text())
versions=sys.argv[1:3] or ['v4','v5']
if len(versions)!=2:raise SystemExit('Pass the previous and current version, e.g. v5 v6')
previous,current=versions
reports={};colors={}
for version in versions:
    folder=ART/'validation'/f'{version}-calibrated'
    data=np.load(folder/'geometry.npz')
    triangles=np.ascontiguousarray(data['triangles'],np.int32)
    labels=np.ascontiguousarray(data['labels'],np.uint8)
    report={}
    for name,camera in cameras.items():
        mask=fit.raster(data['vertices'],name,camera,1,triangles,labels)
        target=fit.TARGETS[name]
        report[name]=dict(zip(['hair','skin','cloth'],fit.overlap(mask,target).tolist()))
        np.save(folder/f'{name}-labels.npy',mask)
        if version==current:
            ref=np.array(Image.open(ART/'reference-inputs'/f'{name}.png').convert('RGB'))
            rendered=np.array(Image.open(folder/f'{name}.png').convert('RGB'))
            colors[name]={}
            for i,label in enumerate(['hair','skin','cloth'],1):
                common=(mask==i)&(target==i)
                colors[name][label]={'reference':np.median(ref[common],axis=0).tolist(),'model':np.median(rendered[common],axis=0).tolist()}
    reports[version]=report
    (folder/'silhouette-scores.json').write_text(json.dumps(report,indent=2))
for name in cameras:
    ref=Image.open(ART/'reference-inputs'/f'{name}.png').convert('RGB');w,h=ref.size
    sheet=Image.new('RGB',(w*3,h+42),'white');draw=ImageDraw.Draw(sheet)
    for i,(label,im) in enumerate([('Approved reference',ref),('Previous model',Image.open(ART/'validation'/f'{previous}-calibrated'/f'{name}.png')),('Revised model',Image.open(ART/'validation'/f'{current}-calibrated'/f'{name}.png'))]):
        draw.text((i*w+12,14),label,fill='black');sheet.paste(im,(i*w,42))
    sheet.save(ART/'validation'/f'{name}-{previous}-{current}.png')
(ART/'validation'/f'comparison-{current}.json').write_text(json.dumps({'silhouetteOverlap':reports,'medianColors':colors},indent=2))
print(json.dumps({'silhouetteOverlap':reports,'medianColors':colors},indent=2))
