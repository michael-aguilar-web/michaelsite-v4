"""Correct the rear skull, nape and profile in a new local v6 scene.

Uses the same reference cameras as v5. The front facial landmarks and website
asset remain untouched until the new scene has been rendered and reviewed.
"""
from pathlib import Path
import bpy, math, runpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART / 'avatar-v5.blend'))


def smooth(a, b, x):
    t = max(0., min(1., (x-a)/(b-a)))
    return t*t*(3-2*t)


def profile(points, z):
    """Monotone cubic interpolation of a measured vertical profile."""
    zz = np.array([p[0] for p in points])
    yy = np.array([p[1] for p in points])
    i = max(0, min(len(points)-2, int(np.searchsorted(zz, z)-1)))
    h = np.diff(zz); d = np.diff(yy)/h
    m = np.zeros(len(zz)); m[0] = d[0]; m[-1] = d[-1]
    for j in range(1, len(zz)-1):
        if d[j-1]*d[j] > 0:
            w1 = 2*h[j]+h[j-1]; w2 = h[j]+2*h[j-1]
            m[j] = (w1+w2)/(w1/d[j-1]+w2/d[j])
    t = max(0, min(1, (z-zz[i])/h[i]))
    return ((2*t**3-3*t*t+1)*yy[i] + (t**3-2*t*t+t)*h[i]*m[i]
            + (-2*t**3+3*t*t)*yy[i+1] + (t**3-t*t)*h[i]*m[i+1])


head = bpy.data.objects['Head — continuous cheeks, jaw and neck']
rear_profile = [
    (.79, .12), (1.0, .12), (1.2, .13), (1.35, .18),
    (1.5, .27), (1.65, .37), (1.8, .49), (1.95, .61),
    (2.1, .70), (2.25, .74), (2.4, .72), (2.55, .65),
    (2.7, .51), (2.85, .38), (3.0, .25), (3.07, .05),
]
# The original head is a ring surface. Preserve the entire front hemisphere
# and its attached facial marks; give the rear hemisphere a continuous skull
# and neck instead of the previous independent Gaussian indentations.
coords = np.array([tuple(v.co) for v in head.data.vertices])
for height in np.unique(coords[:, 2]):
    ids = np.flatnonzero(abs(coords[:, 2]-height) < 1e-6)
    ring = coords[ids]; front = ring[:, 1].min(); back = ring[:, 1].max()
    middle = (front+back)/2
    target = profile(rear_profile, height) - .04*(1-smooth(1.70, 2.05, height))
    for index in ids:
        v = head.data.vertices[int(index)]
        t = max(0., (v.co.y-middle)/max(back-middle, 1e-6))
        v.co.y += (target-back)*t**1.35
head.data.update()

# Rebuild the cap with its rim directly constrained to the skull surface.
# This shares the nape curvature across both meshes; two independently fitted
# surfaces otherwise alternate between a visible gap and skin poking through.
runpy.run_path(str(ROOT/'scripts/avatar-surface-details.py'),
               init_globals={'FIT_NAPE_TO_HEAD': True})
hair = bpy.data.objects['Hair — reference silhouette surface']

bpy.ops.object.select_all(action='DESELECT')
hair.select_set(True); bpy.context.view_layer.objects.active = hair
group = hair.vertex_groups.new(name='Smooth side cap transition')
for v in hair.data.vertices:
    x, y, z = v.co
    angle = abs(math.atan2(x, -(y+.025)))
    weight = math.exp(-.5*((angle-math.pi/2)/.38)**2)
    weight *= smooth(2.12, 2.45, z)*(1-smooth(2.9, 3.1, z))
    if weight > .001:
        group.add([v.index], weight, 'REPLACE')
mod = hair.modifiers.new('Continuous side hair surface', 'SMOOTH')
mod.factor = .75; mod.iterations = 35; mod.vertex_group = group.name
bpy.ops.object.modifier_apply(modifier=mod.name)

bpy.ops.object.select_all(action='DESELECT')
head.select_set(True); bpy.context.view_layer.objects.active = head
mod = head.modifiers.new('Continuous skull surface', 'SUBSURF')
mod.levels = 1; mod.render_levels = 1
bpy.ops.object.modifier_apply(modifier=mod.name)

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART / 'avatar-v6.blend'))
print('Saved corrected profile to avatar-v6.blend', flush=True)
