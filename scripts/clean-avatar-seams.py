"""Remove the intersecting decorative sleeve seams, preserving v11's cloth.

The fine tubes were partly buried in the shirt and could appear as broken,
doubled lines. The sleeve shape already defines the fabric joins, so no
separate seam geometry is needed. Every retained model part stays identical.
"""
from pathlib import Path
import bpy, hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART/'avatar-v11.blend'))
scene = bpy.context.scene

def signature(obj):
    digest = hashlib.sha256()
    digest.update(np.array(obj.matrix_world, dtype=np.float64).tobytes())
    digest.update(np.array([v.co[:] for v in obj.data.vertices], np.float32).tobytes())
    for p in obj.data.polygons:
        digest.update(np.array([*p.vertices, p.material_index, p.use_smooth], np.int32).tobytes())
    for uv in obj.data.uv_layers:
        digest.update(np.array([p.uv[:] for p in uv.data], np.float32).tobytes())
    digest.update('|'.join(m.name for m in obj.data.materials).encode())
    return digest.hexdigest()

parts = [o for o in scene.objects if o.type == 'MESH' and o.get('avatar_part')]
seams = [o for o in parts if o.name.startswith('Raglan seam')]
assert len(seams) == 4, 'Expected exactly four v11 sleeve seam strips'
locked = {o.name: signature(o) for o in parts if o not in seams}
report = {'source': 'v11', 'lockedParts': locked,
          'removedSeams': [o.name for o in seams]}
for obj in seams:
    bpy.data.objects.remove(obj, do_unlink=True)
for name, original in locked.items():
    assert signature(bpy.data.objects[name]) == original, name
report['lockedPartsUnchanged'] = True
(ART/'validation/refinement-v12.json').write_text(json.dumps(report, indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v12.blend'))
print(json.dumps(report, indent=2), flush=True)
