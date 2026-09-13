"""Lift a traced front silhouette onto the hair volume, with a smooth rear cap."""
from pathlib import Path
import bpy, bmesh, math, json
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
refs=bpy.data.collections['REFERENCE — image boards and traced curves']
hair=bpy.data.materials['Ink black hair']
teal=bpy.data.materials['Teal hoodie']
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def mesh(name,verts,faces,mat,part=True):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o)
    o.data.materials.append(mat);o['avatar_part']=part
    for p in o.data.polygons:p.use_smooth=True
    return o

def apply(o):
    active(o);bpy.ops.object.convert(target='MESH')
    return bpy.context.object

def bezier(segments,n=14):
    points=[]
    for p0,p1,p2,p3 in segments:
        for i in range(n):
            t=i/n
            points.append(tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for a,b,c,d in zip(p0,p1,p2,p3)))
    return points

def guide_curve(name,points,closed=False):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D'
    s=d.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*co,1)
    s.use_cyclic_u=closed
    o=bpy.data.objects.new(name,d);refs.objects.link(o)
    o.color=(.8,.12,.08,1);o.show_in_front=True;o.hide_set(True)
    return o

def tuft(name,control,width,thickness):
    points=bezier([control],32)+[control[-1]]
    vs=[];fs=[];sides=20
    for j,p in enumerate(points):
        t=j/(len(points)-1)
        tangent=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])).normalized()
        normal=Vector((tangent.z,0,-tangent.x)).normalized()
        r=max(.001,(1-t)**.72)
        for i in range(sides):
            a=2*math.pi*i/sides
            v=Vector(p)+normal*(width*r*math.cos(a))+Vector((0,thickness*r*math.sin(a),0))
            vs.append(tuple(v))
    for j in range(len(points)-1):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs.append(tuple(reversed(range(sides))));fs.append(tuple((len(points)-1)*sides+i for i in range(sides)))
    return mesh(name,vs,fs,hair)

# Front outline: the bottom follows the approved image; the crown curve omits
# its separate cowlicks. Tessellating in image space avoids twisted meridians.
mask=np.load(ROOT/'artwork/avatar/reference-inputs/three-quarter-labels.npy')==1
edge=np.array([np.flatnonzero(mask[:,x]).max() if mask[:,x].any() else 0 for x in range(mask.shape[1])],float)
kernel=np.exp(-.5*(np.arange(-3,4)/1.0)**2);kernel/=kernel.sum();edge=np.convolve(edge,kernel,mode='same')
upper=bezier([
 ((29,float(edge[29])),(14,180),(34,104),(89,71)),
 ((89,71),(96,68),(77,68),(84,61)),
 ((84,61),(131,23),(210,21),(282,49)),
 ((282,49),(310,74),(331,90),(345,96)),
 ((345,96),(400,109),(426,187),(405,float(edge[405]))),
],28)
outline=upper+[(float(u),float(np.interp(u,np.arange(len(edge)),edge))) for u in np.linspace(405,29,230)[:-1]]
flat=[Vector((u/208,v/208,0)) for u,v in outline]
triangles=tessellate_polygon([flat]);index={tuple(v):i for i,v in enumerate(flat)}
faces=[tuple(v if isinstance(v,int) else index[tuple(v)] for v in f) for f in triangles]
front=mesh('Hair — projected front shell',flat,faces,hair)
bm=bmesh.new();bm.from_mesh(front.data)
for _ in range(9):
 edges=[e for e in bm.edges if e.calc_length()>.034]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
 bmesh.ops.triangulate(bm,faces=list(bm.faces))
bm.to_mesh(front.data);bm.free()
yaw,elev,scale,dx,dy=json.loads((ROOT/'artwork/avatar/validation/calibrated-cameras.json').read_text())['three-quarter']
a,b=map(math.radians,[yaw,elev]);back=np.array([math.sin(a)*math.cos(b),-math.cos(a)*math.cos(b),math.sin(b)])
right=np.array([math.cos(a),math.sin(a),0]);up=np.cross(back,right)
center=np.array([0,-.025,2.365]);radii=np.array([.97,.91,.96])
for vertex in front.data.vertices:
 u,v=vertex.co.x*208,vertex.co.y*208
 p=np.array([0,0,1.72])+right*((u-235-dx)/(208*scale))+up*((370+dy-v)/(208*scale))
 q=(p-center)/radii;d=back/radii;aa=np.dot(d,d);bb=2*np.dot(q,d);cc=np.dot(q,q)-1
 depth=(-bb+math.sqrt(max(0,bb*bb-4*aa*cc)))/(2*aa)
 point=p+back*depth
 # Let the continuous skull cap own the crown. The front outline controls
 # the bangs; fading it into the cap here prevents a thin raised top rim.
 t=max(0,min(1,(v-95)/70));blend=1-t*t*(3-2*t)
 base_radii=np.array([.956,.896,.952]);q=(point-center)/base_radii
 on_cap=center+q/max(np.linalg.norm(q),1e-8)*base_radii*.995
 vertex.co=point*(1-blend)+on_cap*blend
# Close a consistently thin volume toward the skull.
bm=bmesh.new();bm.from_mesh(front.data);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table()
verts=[tuple(v.co) for v in bm.verts];faces=[tuple(v.index for v in f.verts) for f in bm.faces]
border=[(e.verts[0].index,e.verts[1].index) for e in bm.edges if e.is_boundary];bm.free()
count=len(verts);verts += [tuple(np.array(p)+(center-np.array(p))*.085-back*.012) for p in list(verts)]
faces += [tuple(i+count for i in reversed(f)) for f in list(faces)]
faces += [(i,j,j+count,i+count) for i,j in border]
new=bpy.data.meshes.new('Traced front volume');new.from_pydata(verts,[],faces);new.update();front.data=new;new.materials.append(hair)
# Rear half of the hair, kept slightly behind the front surface where they meet.
RX=.956;RY=.896;RZ=.952;YC=-.025;ZC=2.365
N=192;ROWS=55;vs=[];fs=[]
fit_nape=globals().get('FIT_NAPE_TO_HEAD',False)
if fit_nape:
 head=bpy.data.objects['Head — continuous cheeks, jaw and neck']
 bpy.context.view_layer.update()
 head_tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
 head_coords=np.array([tuple(v.co) for v in head.data.vertices])
 heights=np.unique(head_coords[:,2])
 centers=np.array([(head_coords[abs(head_coords[:,2]-z)<1e-6,1].min()+head_coords[abs(head_coords[:,2]-z)<1e-6,1].max())/2 for z in heights])
def eased(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for j in range(ROWS+1):
 t=.001+.999*j/ROWS
 for i in range(N):
  a=2*math.pi*i/N;cs=math.cos(a);sn=math.sin(a)
  rear_angle=(a-math.radians(135)+math.pi)%(2*math.pi)-math.pi
  rear_fit=math.exp(-.5*(rear_angle/math.radians(25))**2)
  ear_angle=(a-math.radians(263)+math.pi)%(2*math.pi)-math.pi
  ear_fit=math.exp(-.5*(ear_angle/math.radians(18))**2)
  lower=2.30+.55*max(cs,0)**3-.55*max(-cs,0)**.75-.15*rear_fit+.10*ear_fit
  if fit_nape:
   side_angle=abs((a+math.pi)%(2*math.pi)-math.pi)
   lower-=.035*math.exp(-.5*((side_angle-math.radians(95))/math.radians(23))**2)
   lower-=.04*max(-cs,0)**.75
  phi=math.acos((lower-ZC)/RZ)*t
  point=Vector(((RX-.08*rear_fit*t**5)*math.sin(phi)*sn,YC-(RY-.16*rear_fit*t**5)*math.sin(phi)*cs,ZC+RZ*math.cos(phi)))
  if fit_nape:
   weight=eased(.68,1,t)*eased(-.28,.08,point.y)
   origin=Vector((0,float(np.interp(point.z,heights,centers)),point.z))
   direction=(point-origin).normalized()
   hit,_,_,_=head_tree.ray_cast(origin,direction)
   if hit is not None:point=point.lerp(hit+direction*.027,weight)
  vs.append(tuple(point))
for j in range(ROWS):
 for i in range(N):
  a=j*N+i;b=j*N+(i+1)%N;fs.append((a,a+N,b+N,b))
outer_count=len(vs);original=list(fs)
vs += [(x*.955,YC+(y-YC)*.955,ZC+(z-ZC)*.955) for x,y,z in list(vs)]
fs += [tuple(outer_count+i for i in reversed(f)) for f in original]
for i in range(N):
 a=ROWS*N+i;b=ROWS*N+(i+1)%N;fs.append((a,b,b+outer_count,a+outer_count))
fs.append(tuple(reversed(range(N))));fs.append(tuple(outer_count+i for i in range(N)))
cap=mesh('Hair — rounded rear shell',vs,fs,hair)
flicks=[
 tuft('Crown flick long',[(.32,.265,3.10),(.39,.30,3.16),(.29,.15,3.35),(.25,.01,3.40)],.115,.105),
 tuft('Crown flick short',[(.45,.35,3.09),(.48,.37,3.17),(.62,.48,3.19),(.57,.46,3.17)],.070,.08),
]
for o in list(scene.objects):
 if o.name.startswith('Hair —') and o not in [front,cap]:bpy.data.objects.remove(o,do_unlink=True)
active(front)
for o in [cap]+flicks:o.select_set(True)
bpy.ops.object.join();front.name='Hair — reference silhouette surface'
bm=bmesh.new();bm.from_mesh(front.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(front.data);bm.free()
front.data.remesh_voxel_size=.006;bpy.ops.object.voxel_remesh()
mod=front.modifiers.new('Round silhouette edges','SMOOTH');mod.factor=.6;mod.iterations=10
group=front.vertex_groups.new(name='Blend crown join')
for v in front.data.vertices:
 z=v.co.z;t=max(0,min(1,(z-2.60)/.24));weight=t*t*(3-2*t)
 if z>3.21 and v.co.x>.1 and v.co.y>-.05:weight=0
 if weight:group.add([v.index],weight,'REPLACE')
mod=front.modifiers.new('Blend the crown surfaces','SMOOTH');mod.factor=1;mod.iterations=100;mod.vertex_group=group.name
mod=front.modifiers.new('Mobile hair mesh','DECIMATE');mod.ratio=.06
apply(front)
for p in front.data.polygons:p.use_smooth=True
print('Rebuilt projected hair surface',flush=True)
