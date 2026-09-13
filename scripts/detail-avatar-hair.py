"""V9: blend the concealed side join and sculpt swept side/back hair clumps.

Starts from the saved v8. The geometry visible from the accepted front cameras
is locked. Details are real mesh geometry and require no browser shader.
"""
from pathlib import Path
import bpy, bmesh, math, heapq, json, runpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART/'avatar-v8.blend'))
runpy.run_path(str(ROOT/'scripts/avatar-side-fillet.py'))
hair = bpy.data.objects['Hair — reference silhouette surface']
original = np.array([tuple(v.co) for v in hair.data.vertices])

def ease(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

vertices, faces = [], []
for part in bpy.context.scene.objects:
    if part.type!='MESH' or not part.get('avatar_part'):continue
    offset=len(vertices)
    vertices.extend(tuple(part.matrix_world@v.co) for v in part.data.vertices)
    faces.extend(tuple(offset+i for i in f.vertices) for f in part.data.polygons)
tree=BVHTree.FromPolygons(vertices,faces)
protected=np.zeros(len(original),bool);front_directions=[]
for yaw in (0,17):
    a,b=math.radians(yaw),math.radians(6)
    direction=Vector((math.sin(a)*math.cos(b),-math.cos(a)*math.cos(b),math.sin(b)))
    front_directions.append(direction)
    for i,v in enumerate(hair.data.vertices):
        hit,_,_,_=tree.ray_cast(v.co+direction*5,-direction,5.04)
        if hit is not None and (hit-v.co).length<.014:protected[i]=True

adjacency=[[] for _ in original]
for edge in hair.data.edges:
    i,j=edge.vertices;distance=float(np.linalg.norm(original[i]-original[j]))
    adjacency[i].append((j,distance));adjacency[j].append((i,distance))
distance=np.full(len(original),np.inf);distance[protected]=0
queue=[(0.,int(i)) for i in np.flatnonzero(protected)];heapq.heapify(queue)
while queue:
    d,i=heapq.heappop(queue)
    if d!=distance[i]:continue
    for j,length in adjacency[i]:
        candidate=d+length
        if candidate<distance[j]:
            distance[j]=candidate;heapq.heappush(queue,(candidate,j))
free=ease(0,.08,distance)

def smooth(weights,iterations,label):
    bpy.ops.object.select_all(action='DESELECT');hair.select_set(True);bpy.context.view_layer.objects.active=hair
    group=hair.vertex_groups.new(name=label);group_name=group.name
    for i in np.flatnonzero(weights>0):group.add([int(i)],float(weights[i]),'REPLACE')
    mod=hair.modifiers.new(label,'SMOOTH');mod.factor=.7;mod.iterations=iterations;mod.vertex_group=group_name
    bpy.ops.object.modifier_apply(modifier=mod.name)
    hair.vertex_groups.remove(hair.vertex_groups[group_name])

# Fair the added backing while retaining the visible front.
center=np.array([0,-.025,2.365]);radii=np.array([.956,.896,.952])
x,y,z=original.T
seam=np.interp(z,[2.39,2.6,2.8,3.,3.15,3.235],[-.325,-.19,-.15,-.10,-.06,-.025])
join=free*(1-ease(-.5,-.25,x))*ease(2.38,2.52,z)*(1-ease(3.16,3.24,z))
join*=np.exp(-.5*((y-seam-.08)/.18)**2)
smooth(join,55,'Round side backing')

# Each lock is a tapered, curved relief on the continuous cap. The asymmetric
# fan follows the crown sweep; the nape and cowlick silhouettes stay quiet.
coords=np.array([tuple(v.co) for v in hair.data.vertices])
directions=(coords-center)/radii
directions/=np.linalg.norm(directions,axis=1)[:,None]
paths=[
    ('Upper swept lock',[(.36,.30,3.13),(-.06,.72,3.02),(-.65,.63,2.87),(-.88,.08,2.65)],.12,.065),
    ('Left swept lock',[(.28,.40,3.09),(-.05,.86,2.75),(-.70,.68,2.40),(-.80,.10,2.23)],.115,.080),
    ('Middle swept lock',[(.36,.60,2.97),(.22,.95,2.61),(-.28,.90,2.21),(-.45,.43,1.99)],.13,.075),
    ('Right swept lock',[(.62,.40,2.96),(.73,.75,2.65),(.47,.75,2.15),(.22,.55,1.91)],.13,.067),
    ('Short temple lock',[(.80,.06,2.94),(.95,.10,2.70),(.85,.20,2.45),(.65,.20,2.22)],.095,.043),
]
height=np.zeros(len(coords))
for name,control,width,amount in paths:
    t=np.linspace(0,1,160);p0,p1,p2,p3=np.array(control)
    path=((1-t)**3)[:,None]*p0+(3*(1-t)**2*t)[:,None]*p1+(3*(1-t)*t*t)[:,None]*p2+(t**3)[:,None]*p3
    path=(path-center)/radii;path/=np.linalg.norm(path,axis=1)[:,None]
    best=np.full(len(coords),-1.);sample=np.zeros(len(coords),int)
    for j,p in enumerate(path):
        dot=directions@p;closer=dot>best;sample[closer]=j;best[closer]=dot[closer]
    cross=np.arccos(np.clip(best,-1,1))
    taper=np.sin(math.pi*t[sample])**1.1
    # Broad relief with a shallow shoulder, avoiding raised strand-like tubes.
    height+=amount*taper*np.exp(-.5*(cross/width)**2)
    height-=amount*.30*taper*np.exp(-.5*((cross-width*1.45)/(width*.24))**2)
z=coords[:,2]
height*=free*ease(1.88,2.15,z)*(1-ease(3.09,3.25,z))
normal=(coords-center)/(radii*radii);normal/=np.linalg.norm(normal,axis=1)[:,None]
for i,v in enumerate(hair.data.vertices):v.co=coords[i]+normal[i]*height[i]
smooth(free*(1-ease(3.20,3.30,z)),12,'Soften small detail edges')

result=np.array([tuple(v.co) for v in hair.data.vertices])
assert np.array_equal(original[protected],result[protected]),'Protected front moved'
# New relief must remain behind the original front surfaces, including the
# silhouette. Locking old visible vertices alone does not prevent a hidden
# clump from growing into view around their edges.
def concealed(point):
    for direction in front_directions:
        hit,_,_,_=tree.ray_cast(point+direction*5,-direction,5.15)
        if hit is None or (point-hit).dot(direction)>-.0015:return False
    return True
limited=0
for i,v in enumerate(hair.data.vertices):
    if protected[i] or np.linalg.norm(result[i]-original[i])<1e-7:continue
    if concealed(v.co):continue
    start=Vector(original[i]);end=v.co.copy();lo,hi=0.,1.
    for _ in range(14):
        middle=(lo+hi)/2
        if concealed(start.lerp(end,middle)):lo=middle
        else:hi=middle
    v.co=start.lerp(end,lo);limited+=1

for face in hair.data.polygons:face.use_smooth=True
hair.data.update()
report={'source':'v8','protectedVertices':int(protected.sum()),
        'frontMaxDisplacement':float(np.linalg.norm(result[protected]-original[protected],axis=1).max()),
        'maxPreClampDetailDisplacement':float(np.linalg.norm(result-original,axis=1).max()),
        'hullLimitedVertices':limited,
        'finalVertices':len(hair.data.vertices),
        'locks':[p[0] for p in paths]}
(ART/'validation/refinement-v9.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v9.blend'))
print(json.dumps(report,indent=2),flush=True)
