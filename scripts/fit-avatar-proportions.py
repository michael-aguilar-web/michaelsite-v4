"""Fit the existing detailed meshes to a measured side-profile shape cage.

Unlike the base model's elliptical cross-sections, this pass controls the front
and back silhouette independently at each height. The face marks, skull, and
hair share the same smooth deformation, preserving their attachment. Clothing
is fitted as separate anatomical regions so deeper sleeves cannot swallow the
chest. Run with Blender --background --python; AVATAR_DRAFT=1 keeps it local to
artwork/avatar until the renders have been reviewed.
"""
from pathlib import Path
import bpy
import math
import os
import json
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artwork/avatar'
guide=json.loads((OUT/'proportion-guides.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'avatar-v2.blend'))
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=='MESH']
for o in objects:
    # All cage coordinates are world-space; bake object scale before fitting.
    world=o.matrix_world.copy()
    for v in o.data.vertices:v.co=world@v.co
    o.matrix_world=Matrix.Identity(4)


def curve(xs,ys):
    """Monotone cubic Hermite interpolation, without third-party dependencies."""
    n=len(xs)
    h=[xs[i+1]-xs[i] for i in range(n-1)]
    d=[(ys[i+1]-ys[i])/h[i] for i in range(n-1)]
    slopes=[d[0]]+[0]*(n-2)+[d[-1]]
    for i in range(1,n-1):
        if d[i-1]*d[i]>0:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1]
            slopes[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    def evaluate(x):
        if x<=xs[0]:return ys[0]
        if x>=xs[-1]:return ys[-1]
        low=0;high=n-1
        while high-low>1:
            mid=(low+high)//2
            if xs[mid]>x:high=mid
            else:low=mid
        i=low;t=(x-xs[i])/h[i]
        return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h[i]*slopes[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h[i]*slopes[i+1]
    return evaluate


def smoothstep(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)

head=next(o for o in objects if o.name.startswith('Head —'))
slices={}
for v in head.data.vertices:
    slices.setdefault(round(v.co.z,6),[]).append(v.co.y)
levels=sorted(slices)
source_front=curve(levels,[min(slices[z]) for z in levels])
source_back=curve(levels,[max(slices[z]) for z in levels])
zs=[p[0] for p in guide['headProfile']]
unit=guide['referencePixelsPerUnit'];origin=guide['sideOriginX']
target_front=curve(zs,[(p[1]-origin)/unit for p in guide['headProfile']])
target_back=curve(zs,[(p[2]-origin)/unit for p in guide['headProfile']])


def averaged(fn, z, sigma=.045):
    # Smooth the sampled 2D boundary into a continuously curved 3D silhouette.
    weights=[math.exp(-.5*(i/2.0)**2) for i in range(-6,7)]
    return sum(fn(z+i*sigma/2)*w for i,w in zip(range(-6,7),weights))/sum(weights)

# Bake the filtered cage to lookup curves; do not refilter for every vertex.
fit_z=[.79+i*(3.069-.79)/400 for i in range(401)]
fit_front=curve(fit_z,[averaged(target_front,z) for z in fit_z])
fit_back=curve(fit_z,[averaged(target_back,z) for z in fit_z])
hair_z=[p[0] for p in guide['sideSilhouette'] if p[0]>=1.6]
hair_back=curve(hair_z,[(p[2]-origin)/unit for p in guide['sideSilhouette'] if p[0]>=1.6])


def skull_y(y,z):
    a,b=source_front(z),source_back(z)
    aa,bb=fit_front(z),fit_back(z)
    if b-a<.005:return (aa+bb)*.5+(y-(a+b)*.5)
    if y<a:return aa+(y-a)*.9
    if y>b:return bb+(y-b)*.9
    return aa+(y-a)/(b-a)*(bb-aa)


def hair_shape(x,y,z):
    # Preserve the front hairstyle and fit the back of the skull separately.
    # Its nape wraps down and inward, as in the side reference.
    rear=smoothstep(.08,.50,y)
    low=1-smoothstep(1.80,2.43,z)
    new_z=z-.185*rear*low
    new_y=y*1.20-.04
    if y>.065 and z<2.87:
        source_edge=.065+.665*math.sqrt(max(.01,1-((z-2.33)/.87)**2))
        factor=max(0,min(1.03,(y-.065)/(source_edge-.065)))
        destination=.038+factor*(averaged(hair_back,new_z,.035)-.038)
        blend=1-smoothstep(2.70,2.87,z)
        new_y=new_y*(1-blend)+destination*blend
    return x,new_y,new_z


def bounds(parts):
    verts=[v.co for o in parts for v in o.data.vertices]
    return {axis:round(max(v[i] for v in verts)-min(v[i] for v in verts),4) for i,axis in enumerate(['width','depth','height'])}

parts={
    'head':[head],
    'headAndHair':[o for o in objects if o.name.startswith(('Head —','Hair —','Ear '))],
    'chest':[o for o in objects if o.name=='Hoodie body'],
    'bodyAndSleeves':[o for o in objects if o.name.startswith(('Hoodie body','Soft raglan'))],
}
report={'before':{k:bounds(v) for k,v in parts.items()}}
for o in objects:
    for v in o.data.vertices:
        x,y,z=v.co
        if o.name.startswith(('Head —','Flat dot eye','Fine curved smile')):
            y=skull_y(y,z)
        elif o.name.startswith('Hair —'):
            x,y,z=hair_shape(x,y,z)
        elif o.name.startswith('Ear '):
            y+=guide['ears']['targetCenter']-guide['ears']['sourceCenter']
        elif o.name.startswith(('Soft raglan sleeve','Raglan seam')):
            g=guide['sleeves'];y=(y-g['sourceCenter'])*g['depthScale']+g['targetCenter']
        elif o.name.startswith('Hood —'):
            g=guide['hood'];y=y*g['depthScale']+g['offset']
        else:
            g=guide['chest'];y=y*g['depthScale']+g['offset']
        v.co=(x,y,z)
    o.data.update()
    if o.name.startswith('Hood drawstring'):
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
        bm.to_mesh(o.data);bm.free()
report['after']={k:bounds(v) for k,v in parts.items()}
report['ratios']={
    stage:{
        'headDepthToWidth':round(report[stage]['head']['depth']/report[stage]['head']['width'],3),
        'chestDepthToShoulderWidth':round(report[stage]['chest']['depth']/report[stage]['bodyAndSleeves']['width'],3),
    }for stage in ['before','after']
}
(OUT/'proportions-v3.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)

# Refit a consistent, slightly elevated orthographic camera for all views.
cam=scene.camera
cam.data.ortho_scale=4.05
scene.render.resolution_x=800;scene.render.resolution_y=1000
scene.cycles.samples=64
views=[('front',(0,-8,2.62)),('three-quarter',(2.45,-8,2.62)),('side',(8,0,2.62)),('other-side',(-8,0,2.62)),('rear',(3.4,7,2.62))]
for name,pos in views:
    cam.location=pos
    cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'{name}.png')
    bpy.ops.render.render(write_still=True)
cam.location=views[1][1];cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'avatar-v3.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
export_path=OUT/'avatar-v3.glb' if os.environ.get('AVATAR_DRAFT') else ROOT/'public/models/avatar.glb'
bpy.ops.export_scene.gltf(filepath=str(export_path),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
print('Exported',export_path,flush=True)
