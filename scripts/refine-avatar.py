"""Apply the measured reference fit to the editable Blender avatar.

Saves a new local version. It never replaces the website asset automatically.
"""
from pathlib import Path
import bpy, bmesh, json, math, sys, runpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART/'avatar-v4.blend'))
scene=bpy.context.scene
fit=np.load(ART/'validation/v5-fit/fitted-vertices.npy')
parts=json.loads((ART/'validation/v4/parts.json').read_text())
for name,(a,b) in parts.items():
    obj=bpy.data.objects[name]
    if len(obj.data.vertices)!=b-a:raise RuntimeError(f'Vertex count changed for {name}')
    obj.matrix_world=Matrix.Identity(4)
    obj.data.vertices.foreach_set('co',fit[a:b].ravel())
    obj.data.update()

# Match the eye line and the visibility of the ears in the portrait and side
# reference. Keep the ink attached to the skin after moving the landmarks.
head=bpy.data.objects['Head — continuous cheeks, jaw and neck']
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for v in head.data.vertices:
    x,y,z=v.co
    g=smooth(.05,.40,y)*math.exp(-.5*((z-1.8)/.30)**2)
    v.co.y-=.18*g
head.data.update()
head_tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
for obj in scene.objects:
    if obj.name.startswith(('Flat dot eye','Eye ink rim','Fine curved smile')):
        for v in obj.data.vertices:
            old,_,_,_=head_tree.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)))
            z=v.co.z+.04+.06*v.co.x
            new,_,_,_=head_tree.ray_cast(Vector((v.co.x,-3,z)),Vector((0,1,0)))
            if old is not None and new is not None:v.co.y+=new.y-old.y
            v.co.z=z
        obj.data.update()
    elif obj.name.startswith('Ear '):
        for v in obj.data.vertices:v.co.y-=.10;v.co.z+=.02
        obj.data.update()

runpy.run_path(str(ROOT/'scripts/avatar-surface-details.py'))

# A shallower front fold opens into a broad hanging hood at the back.
hood=bpy.data.objects['Hood — traced neckline and back']
vs=[];fs=[];n=160;sides=48
for i in range(n):
    a=2*math.pi*i/n;sn=math.sin(a);cs=math.cos(a)
    front=max(cs,0);rear=max(-cs,0)
    vee=front*(1-(math.sqrt(sn*sn+.0004)-.02)**.85)
    center=1.03+.06*front-.315*vee
    for j in range(sides):
        b=2*math.pi*j/sides;c=math.cos(b);s=math.sin(b)
        x=(.575+.245*c)*sn+.11-.11*front**4
        y=.04-(.51-.16*front+(.20+.045*front)*c)*cs
        z=center+(.16-.06*front)*s-.36*rear**1.15*max(-s,0)**1.3
        vs.append((x*1.08,y,z))
for i in range(n):
    for j in range(sides):fs.append((i*sides+j,((i+1)%n)*sides+j,((i+1)%n)*sides+(j+1)%sides,i*sides+(j+1)%sides))
mesh=bpy.data.meshes.new('Hood folded surface');mesh.from_pydata(vs,[],fs);mesh.update()
lining=bpy.data.materials.get('Hood lining')
if lining is None:
    lining=bpy.data.materials['Teal hoodie'].copy();lining.name='Hood lining'
    lining.diffuse_color=(.002,.037,.046,1)
    lining.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=lining.diffuse_color
hood.data=mesh;mesh.materials.append(bpy.data.materials['Teal hoodie']);mesh.materials.append(lining)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
for f in mesh.polygons:
    f.use_smooth=True
    f.material_index=1 if math.cos(2*math.pi*(f.index%sides+.5)/sides)<-.62 else 0

# Preserve the supplied logo pixels, while matching its smaller, cropped
# placement in the reference. Re-project every vertex onto the fitted shirt.
body=bpy.data.objects['Hoodie body'];tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
logo=bpy.data.objects['BEAN 1833 — surface print']
for v in logo.data.vertices:
    v.co.x=v.co.x*.85-.025;v.co.z=v.co.z*.85-.16
bm=bmesh.new();bm.from_mesh(logo.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,.003),plane_no=(0,0,1),clear_inner=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(logo.data);bm.free()
for v in logo.data.vertices:
    hit,_,_,_=tree.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)))
    if hit is None:raise RuntimeError('Logo vertex lies outside the shirt')
    v.co.y=hit.y-.004
logo.data.update()

# Add softly rounded cord ends and fit their upper ends to the collar.
for old in [o for o in scene.objects if o.name.startswith('Hood drawstring')]:
    side=-1 if sum(v.co.x for v in old.data.vertices)<0 else 1
    bpy.data.objects.remove(old,do_unlink=True)
    x=side*.225-.025
    hood_tree=BVHTree.FromObject(hood,bpy.context.evaluated_depsgraph_get())
    points=[]
    for z in [.70,.65,.58,.46,.30,.16,0]:
        xx=x+side*.045*(1-z/.7)
        hits=[h for h in [tree.ray_cast(Vector((xx,-3,max(z,.004))),Vector((0,1,0)))[0],hood_tree.ray_cast(Vector((xx,-3,z)),Vector((0,1,0)))[0]] if h is not None]
        points.append((xx,min(h.y for h in hits)-.037,z))
    data=bpy.data.curves.new('Hood drawstring','CURVE');data.dimensions='3D';data.bevel_depth=.035;data.bevel_resolution=4;data.resolution_u=24;data.use_fill_caps=True
    spline=data.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    obj=bpy.data.objects.new('Hood drawstring',data);scene.collection.objects.link(obj);data.materials.append(bpy.data.materials['Warm white drawstrings']);obj['avatar_part']=True
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.035,location=points[0])
    end=bpy.context.object;end.name='Drawstring rounded end';end.data.materials.append(bpy.data.materials['Warm white drawstrings']);end['avatar_part']=True
    for f in end.data.polygons:f.use_smooth=True

# Broad, neutral fill prevents the cheeks and neck falling into brown shadow.
world_mix=next(n for n in scene.world.node_tree.nodes if n.bl_idname=='ShaderNodeMixRGB')
world_mix.inputs[1].default_value=(.64,.64,.64,1)
for name,power in [('Softbox above left',265),('Soft front fill',155),('Soft rim',155)]:bpy.data.objects[name].data.energy=power
def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
for name,rgb in [('Teal hoodie','03809B'),('Teal seam','04788F'),('Peach skin','D48D64'),('Ink black hair','141414')]:
    material=bpy.data.materials[name]
    color=tuple(linear(int(rgb[i:i+2],16)/255) for i in [0,2,4])
    material.diffuse_color=(*color,1)
    shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(*color,1)
    if name=='Peach skin':shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=.08

scene.cycles.samples=64
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v5.blend'))
print('Saved fitted model locally',flush=True)
