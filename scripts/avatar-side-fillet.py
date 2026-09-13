"""Add a closed backing volume to the side fringe without moving its front."""
import bpy,bmesh,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

hair=bpy.data.objects['Hair — reference silhouette surface']
hair_tree=BVHTree.FromObject(hair,bpy.context.evaluated_depsgraph_get())
vs,fs=[],[]
for part in bpy.context.scene.objects:
    if part.type!='MESH' or not part.get('avatar_part'):continue
    offset=len(vs);vs.extend(tuple(part.matrix_world@v.co) for v in part.data.vertices)
    fs.extend(tuple(offset+i for i in f.vertices) for f in part.data.polygons)
tree=BVHTree.FromPolygons(vs,fs)
directions=[]
for yaw in (0,17):
    a,b=math.radians(yaw),math.radians(6)
    directions.append(Vector((math.sin(a)*math.cos(b),-math.cos(a)*math.cos(b),math.sin(b))))

def ease(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def concealed(point):
    for direction in directions:
        hit,_,_,_=tree.ray_cast(point+direction*5,-direction,5.15)
        if hit is None or (point-hit).dot(direction)>-.0015:return False
    return True

rows,cols=101,73
zz=np.linspace(2.39,3.235,rows);uu=np.linspace(-.055,.30,cols)
outer=np.zeros((rows,cols,3))
for j,z in enumerate(zz):
    seam=float(np.interp(z,[2.39,2.6,2.8,3.,3.15,3.235],[-.325,-.19,-.15,-.10,-.06,-.025]))
    samples=[]
    for u in uu:
        y=seam+u;hit,_,_,_=hair_tree.ray_cast(Vector((-2,y,z)),Vector((1,0,0)))
        samples.append(hit.x if hit is not None and hit.x<-.2 else np.nan)
    valid=np.flatnonzero(np.isfinite(samples))
    if not len(valid):raise RuntimeError(f'No left cap at height {z}')
    # A ray can pass through the old seam and hit the opposite side. Bridge
    # those gaps from the neighboring left surface, never from the far side.
    samples=np.interp(np.arange(cols),valid,np.asarray(samples)[valid]).tolist()
    limit=min(samples)+.006
    for i,u in enumerate(uu):
        fade=float(ease(2.39,2.51,z)*(1-ease(3.17,3.235,z))*ease(-.055,-.005,u)*(1-ease(.22,.30,u)))
        strength=fade*math.exp(-.5*((u-.045)/.15)**2)
        rounded_limit=limit+.45*(u+.02)**2
        outer[j,i]=[max(rounded_limit,samples[i]+.020-.19*strength),seam+u,z]
for _ in range(18):
    x=outer[:,:,0].copy()
    outer[1:-1,1:-1,0]=.6*x[1:-1,1:-1]+.1*(x[:-2,1:-1]+x[2:,1:-1]+x[1:-1,:-2]+x[1:-1,2:])
for j in range(rows):
    for i in range(cols):
        point=Vector(outer[j,i]);inside=point+Vector((.28,0,0))
        if not concealed(point):
            if not concealed(inside):raise RuntimeError(f'Side patch leaves protected front at {tuple(point)}, {tuple(inside)}')
            lo,hi=0.,1.
            for _ in range(16):
                t=(lo+hi)/2
                if concealed(point.lerp(inside,t)):hi=t
                else:lo=t
            point=point.lerp(inside,hi)
        outer[j,i]=point
vertices=outer.reshape(-1,3).tolist();count=len(vertices)
vertices += [(x+.28,y,z) for x,y,z in vertices]
faces=[]
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i;b=a+1;c=b+cols;d=a+cols
        faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
rim=list(range(cols))+[j*cols+cols-1 for j in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[j*cols for j in range(rows-2,0,-1)]
for a,b in zip(rim,rim[1:]+rim[:1]):faces.append((a,a+count,b+count,b))
mesh=bpy.data.meshes.new('Concealed side fillet');mesh.from_pydata(vertices,[],faces);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
patch=bpy.data.objects.new('Concealed side fillet',mesh);bpy.context.scene.collection.objects.link(patch)
patch.data.materials.append(bpy.data.materials['Ink black hair'])
bpy.ops.object.select_all(action='DESELECT');hair.select_set(True);bpy.context.view_layer.objects.active=hair
mod=hair.modifiers.new('Continuous fringe-to-cap volume','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=patch
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(patch,do_unlink=True)
bm=bmesh.new();bm.from_mesh(hair.data)
if any(not e.is_manifold for e in bm.edges):raise RuntimeError('Side union is not manifold')
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(hair.data);bm.free();hair.data.update()
print('Side fillet merged:',len(hair.data.vertices),'vertices',flush=True)
