"""Build v11's continuous sleeves and fit the hood around both shoulders.

Starts from the saved v10. The accepted head and facial marks are locked.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART/'avatar-v10.blend'))
scene=bpy.context.scene

def ease(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)

def signature(obj):
    digest=hashlib.sha256()
    digest.update(np.array(obj.matrix_world,dtype=np.float64).tobytes())
    digest.update(np.array([v.co[:] for v in obj.data.vertices],np.float32).tobytes())
    for p in obj.data.polygons:
        digest.update(np.array([*p.vertices,p.material_index,p.use_smooth],np.int32).tobytes())
    for uv in obj.data.uv_layers:
        digest.update(np.array([p.uv[:] for p in uv.data],np.float32).tobytes())
    digest.update('|'.join(m.name for m in obj.data.materials).encode())
    return digest.hexdigest()

def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj

def tree(obj):
    bpy.context.view_layer.update()
    return BVHTree.FromObject(obj,bpy.context.evaluated_depsgraph_get())

def topology(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    remaining=set(bm.verts);components=[]
    while remaining:
        stack=[remaining.pop()];count=0
        while stack:
            v=stack.pop();count+=1
            for e in v.link_edges:
                other=e.other_vert(v)
                if other in remaining:remaining.remove(other);stack.append(other)
        components.append(count)
    report={'vertices':len(bm.verts),'boundaryEdges':sum(e.is_boundary for e in bm.edges),
            'nonmanifoldEdges':sum(not e.is_manifold for e in bm.edges),'components':components}
    bm.free();return report

locked={o.name:signature(o) for o in scene.objects if o.type=='MESH' and o.get('avatar_part')
        and o.name.startswith(('Hair','Head','Ear','Flat','Fine','Eye'))}
report={'source':'v10','lockedParts':locked}
body=bpy.data.objects['Hoodie body'];original_body_tree=tree(body)
logo=bpy.data.objects['BEAN 1833 — surface print']
original_logo_uv=np.array([d.uv[:] for d in logo.data.uv_layers.active.data])

# Give the sleeves a rounded cap and enough depth at the front. The earlier
# sleeves were narrow rearward columns intersecting the torso.
for name in ('Soft raglan sleeve','Soft raglan sleeve.001'):
    sleeve=bpy.data.objects[name]
    for v in sleeve.data.vertices:
        x,y,z=v.co
        side=1 if x>0 else -1
        v.co.y-=.18*(1-ease(.02,.50,y))
        v.co.x+=side*.022*ease(.20,.72,z)
        v.co.z+=.025*math.exp(-((z-.70)/.20)**2)
    sleeve.data.update()

# Fuse torso and arms into one closed fabric surface. Smooth the shoulder
# joins as geometry, then add restrained sewn seams on that shared surface.
active(body)
for name in ('Soft raglan sleeve','Soft raglan sleeve.001'):bpy.data.objects[name].select_set(True)
bpy.ops.object.join()
body.data.remesh_voxel_size=.010
body.data.use_remesh_preserve_volume=True
bpy.ops.object.voxel_remesh()
group=body.vertex_groups.new(name='Round shoulder joins')
for v in body.data.vertices:
    x,y,z=v.co
    weight=ease(.07,.22,z)*(.25+.75*ease(.37,.67,abs(x)))
    group.add([v.index],weight,'REPLACE')
mod=body.modifiers.new('Soft sleeve caps','SMOOTH');mod.factor=.75;mod.iterations=24;mod.vertex_group=group.name
bpy.ops.object.modifier_apply(modifier=mod.name)
body.vertex_groups.remove(body.vertex_groups['Round shoulder joins'])

# Keep the central chest's depth, which supports the supplied logo and cords.
# Leave enough unmodified cloth around its edges to blend into the sleeves.
for v in body.data.vertices:
    x,y,z=v.co
    w=(1-ease(.45,.72,abs(x)))*(1-ease(-.32,-.04,y))
    if w:
        hit=original_body_tree.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))[0]
        if hit is not None:v.co.y+=(hit.y-y)*w
    if z<.025:v.co.z-=.012*(1-ease(-.01,.025,z))
body.data.update()

# Center the hood on the spine and let the outer shoulder folds fall down.
# The front neckline and its embedded drawstring sockets stay in place.
hood=bpy.data.objects['Hood — traced neckline and back']
for v in hood.data.vertices:
    i,j=divmod(v.index,64)
    a=2*math.pi*i/192;b=2*math.pi*j/64
    front=max(math.cos(a),0.);side=abs(math.sin(a));outer=max(math.cos(b),0.)
    rear_weight=1-ease(.40,.85,front)
    v.co.x-=1.08*.095*(1-front**4)*rear_weight
    v.co.z-=.050*side**4*(.35+.65*outer)*rear_weight
    # An arch over the sleeve cap exposes its rounded shoulder. A level
    # underside hid that curvature and made the sleeve look cut off square.
    v.co.z+=side**6*(.075*max(-math.sin(b),0.)**.85+.025*outer)
hood.data.update()
active(hood)
group=hood.vertex_groups.new(name='Round the rear fold')
for v in hood.data.vertices:
    a=2*math.pi*(v.index//64)/192
    group.add([v.index],1-ease(.45,.85,max(math.cos(a),0.)),'REPLACE')
mod=hood.modifiers.new('Relax folded edge','SMOOTH');mod.factor=.45;mod.iterations=8;mod.vertex_group=group.name
bpy.ops.object.modifier_apply(modifier=mod.name)
hood.vertex_groups.remove(hood.vertex_groups['Round the rear fold'])

# Cut a clean, planar hem after remeshing, removing voxel stair-steps.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                      dist=1e-6,plane_co=(0,0,-.005),plane_no=(0,0,1),clear_inner=True)
boundary=[e for e in bm.edges if e.is_boundary]
if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(body.data);bm.free();body.data.update()

# Reduce the remeshed surface without changing the accepted head's topology.
active(body)
mod=body.modifiers.new('Clothing web topology','DECIMATE');mod.ratio=.24
bpy.ops.object.modifier_apply(modifier=mod.name)
for f in body.data.polygons:f.use_smooth=True
body.data.update();body_tree=tree(body)

# Resolve contact by lifting the outer hood over the rounded shoulders, not
# flattening the shoulder caps. Relax the displacement along the cloth so the
# contact edge stays rounded. The inner lining can remain tucked into the neck.
original=np.array([v.co[:] for v in hood.data.vertices]).reshape(192,64,3)
offsets=np.zeros_like(original)
weights=np.zeros((192,64))
contacts=0
for i in range(192):
    a=2*math.pi*i/192;front=max(math.cos(a),0.)
    for j in range(64):
        c=math.cos(2*math.pi*j/64)
        weight=(1-ease(.45,.85,front))*ease(-.60,-.20,c)
        weights[i,j]=weight
        if weight==0:continue
        p=Vector(original[i,j]);near,normal,_,_=body_tree.find_nearest(p)
        signed=(p-near).dot(normal)
        if signed<.018:
            offsets[i,j]=np.array(normal)*(.018-signed)*weight
            contacts+=1
for _ in range(36):
    adjacent=(np.roll(offsets,1,0)+np.roll(offsets,-1,0)+np.roll(offsets,1,1)+np.roll(offsets,-1,1))/4
    offsets=.65*offsets+.35*adjacent*weights[:,:,None]
for i in range(192):
    for j in range(64):
        p=Vector(original[i,j]+offsets[i,j])
        if weights[i,j]>.99:
            near,normal,_,_=body_tree.find_nearest(p)
            signed=(p-near).dot(normal)
            if signed<.012:p+=normal*(.012-signed)
        hood.data.vertices[i*64+j].co=p
hood.data.update()
report['hoodContactVertices']=contacts

# Replace the old raised intersecting seam strips with fine surface seams.
for o in list(scene.objects):
    if o.name.startswith('Raglan seam'):bpy.data.objects.remove(o,do_unlink=True)
seam_mat=bpy.data.materials['Teal seam']
for side in (-1,1):
    for rear in (False,True):
        points=[]
        for t in np.linspace(0,1,24):
            z=.02+.89*t
            x=side*(.715-.195*t**2)
            direction=Vector((0,-1 if rear else 1,0))
            origin=Vector((x,3 if rear else -3,z))
            hit,normal,_,_=body_tree.ray_cast(origin,direction)
            if hit is not None:points.append(hit+normal*.0005)
        if len(points)<4:raise RuntimeError('Sleeve seam misses the cloth')
        data=bpy.data.curves.new('Fitted raglan seam','CURVE');data.dimensions='3D'
        data.bevel_depth=.0028;data.bevel_resolution=1;data.resolution_u=3
        spline=data.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
        for p,co in zip(spline.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
        obj=bpy.data.objects.new('Raglan seam',data);scene.collection.objects.link(obj)
        obj['avatar_part']=True;data.materials.append(seam_mat)
        active(obj);bpy.ops.object.convert(target='MESH')
        for f in obj.data.polygons:f.use_smooth=True

# Keep the actual artwork and its UVs; only reseat the print on the new shirt.
for v in logo.data.vertices:
    hit=body_tree.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)))[0]
    if hit is None:raise RuntimeError(f'Print outside shirt at {v.co[:]}')
    v.co.y=hit.y-.004
logo.data.update()
assert np.array_equal(original_logo_uv,np.array([d.uv[:] for d in logo.data.uv_layers.active.data]))
report['logoUVsUnchanged']=True
for name,digest in locked.items():assert signature(bpy.data.objects[name])==digest,name
report['lockedPartsUnchanged']=True
report['bodyTopology']=topology(body);report['hoodTopology']=topology(hood)
for item in ('bodyTopology','hoodTopology'):
    assert report[item]['nonmanifoldEdges']==0,report[item]
    assert len(report[item]['components'])==1,report[item]
(ART/'validation/refinement-v11.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v11.blend'))
print(json.dumps(report,indent=2),flush=True)
