"""Refine the avatar using packed reference boards and traced Bezier guides.

The reference geometry is kept in its own non-rendering collection and omitted
from the web export. The supplied BEAN artwork is UV mapped without redrawing
or extruding its lettering. AVATAR_DRAFT=1 leaves the live local asset alone.
"""
from pathlib import Path
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'avatar-v3.blend'))
scene=bpy.context.scene
for o in scene.objects:
    if o.type=='MESH':o['avatar_part']=True
refs=bpy.data.collections.new('REFERENCE — image boards and traced curves')
scene.collection.children.link(refs);refs.hide_render=True


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

hair=bpy.data.materials['Ink black hair']
teal=bpy.data.materials['Teal hoodie']

# Front fringe traced as curved segments, rather than overlapping pillow forms.
# These x/z landmarks follow the reference; their depth lies on the fuller
# cranial volume established by the measured side silhouette.
fringe_segments=[
    ((-.93,.13,2.25),(-1.0,-.09,2.25),(-.96,-.40,2.22),(-.87,-.52,2.24)),
    ((-.87,-.52,2.24),(-.73,-.60,2.30),(-.59,-.655,2.43),(-.55,-.68,2.515)),
    ((-.55,-.68,2.515),(-.56,-.74,2.46),(-.61,-.81,2.373),(-.60,-.83,2.363)),
    ((-.60,-.83,2.363),(-.365,-.91,2.377),(-.032,-.90,2.473),(.217,-.87,2.614)),
    ((.217,-.87,2.614),(.235,-.86,2.52),(.30,-.84,2.447),(.365,-.82,2.411)),
    ((.365,-.82,2.411),(.336,-.78,2.493),(.336,-.735,2.570),(.344,-.735,2.659)),
    ((.344,-.735,2.659),(.401,-.75,2.461),(.548,-.63,2.356),(.704,-.535,2.275)),
    ((.704,-.535,2.275),(.703,-.49,2.303),(.672,-.45,2.349),(.686,-.43,2.387)),
    ((.686,-.43,2.387),(.753,-.405,2.267),(.801,-.36,2.249),(.817,-.335,2.265)),
    ((.817,-.335,2.265),(.86,-.20,2.30),(.902,.01,2.379),(.942,.09,2.252)),
]
fringe=bezier(fringe_segments,16)+[fringe_segments[-1][-1]]
# Use a broad cranium with one continuous curved surface.
RX=.97;RY=.91;RZ=.96;ZC=2.365;YC=-.025
boundary=list(fringe)
# Join around the ear to a lower, inward-curving nape.
right=boundary[-1];left=boundary[0]
a0=math.atan2(right[0]/RX,-(right[1]-YC)/RY)
a1=math.atan2(left[0]/RX,-(left[1]-YC)/RY)+2*math.pi
for i in range(1,97):
    t=i/97;a=a0+(a1-a0)*t
    rear=max(-math.cos(a),0)
    z=2.25-.595*rear**1.1
    phi=math.acos((z-ZC)/RZ)
    boundary.append((RX*math.sin(phi)*math.sin(a),YC-RY*math.sin(phi)*math.cos(a),z))
guide_curve('Trace — fringe and nape',boundary,True)

angles=[];phis=[]
previous=None
for i,(x,y,z) in enumerate(boundary):
    a=math.atan2(x/RX,-(y-YC)/RY)
    if previous is not None:
        while a<previous-math.pi:a+=2*math.pi
        # A returning strand must project forward, rather than crossing its
        # neighbour inside the cap. Keep the radial ordering of the surface.
        a=max(a,previous+.0015)
        if i<len(fringe) and abs(math.sin(a))>.05:
            y=YC-(x/RX)/math.tan(a)*RY
            boundary[i]=(x,y,z)
    angles.append(a);previous=a
    phis.append(math.acos(max(-1,min(1,(z-ZC)/RZ))))
# Topology follows an ordered circle at the crown, then the traced fringe.
# This permits the little returning tips without stacking separate hair caps.
N=len(boundary);ROWS=44;vs=[];fs=[]
for j in range(ROWS+1):
    t=.001+(1-.001)*j/ROWS
    for i,(a,phi) in enumerate(zip(angles,phis)):
        regular=angles[0]+(2*math.pi)*i/N
        theta=regular*(1-t**8)+a*t**8
        p=phi*t
        sn=math.sin(p)
        # A subtle leftward sweep gives the crown its asymmetric silhouette.
        x=RX*sn*math.sin(theta)-.035*(1-t)**2
        y=YC-RY*sn*math.cos(theta)
        z=ZC+RZ*math.cos(p)
        # The traced tips may sit just outside the spherical surface. Blend
        # their exact boundary positions into the last part of each meridian.
        bx,by,bz=boundary[i]
        x+=(bx-RX*math.sin(phi)*math.sin(a))*t**12
        y+=(by-YC+RY*math.sin(phi)*math.cos(a))*t**12
        # The upper left sweep turns outward and then folds into the crown.
        sweep=math.exp(-((theta+1.14)/.43)**2)
        x+=sweep*(-.14*math.exp(-((z-3.13)/.042)**2)+.045*math.exp(-((z-3.072)/.022)**2))
        bulge=.035*math.exp(-((theta+.45)/.55)**2)*sn**2
        y-=bulge
        vs.append((x,y,z))
for j in range(ROWS):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;fs.append((a,a+N,b+N,b))
vs.append((0,0,2.40));c=len(vs)-1
for i in range(N):fs.append((ROWS*N+i,c,ROWS*N+(i+1)%N))
fs.append(tuple(reversed(range(N))))
cap=mesh('Hair — reference curve loft',vs,fs,hair)
for o in list(scene.objects):
    if o.name.startswith('Hair —') and o!=cap:bpy.data.objects.remove(o,do_unlink=True)


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

flicks=[
    tuft('Crown flick long',[(.31,.25,3.135),(.40,.30,3.24),(.315,.19,3.382),(.235,.085,3.437)],.105,.12),
    tuft('Crown flick short',[(.46,.39,3.115),(.515,.49,3.22),(.62,.64,3.30),(.672,.70,3.269)],.083,.095),
]
active(cap)
for o in flicks:o.select_set(True)
bpy.ops.object.join()
bm=bmesh.new();bm.from_mesh(cap.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cap.data);bm.free()
cap.data.remesh_voxel_size=.008;bpy.ops.object.voxel_remesh()
mod=cap.modifiers.new('Polish continuous curves','SMOOTH');mod.factor=.7;mod.iterations=6
mod=cap.modifiers.new('Mobile mesh','DECIMATE');mod.ratio=.06
apply(cap)
for p in cap.data.polygons:p.use_smooth=True

# Loft the neckline and hanging hood as one surface. Its cross-section deepens
# continuously toward the back, so there is no separate roll perched on a flap.
old_hood=next(o for o in scene.objects if o.name.startswith('Hood —'))
bpy.data.objects.remove(old_hood,do_unlink=True)
vs=[];fs=[];n=160;sides=48;neckline=[]
for i in range(n):
    a=2*math.pi*i/n;sn=math.sin(a);cs=math.cos(a)
    front=max(cs,0);rear=max(-cs,0)
    vee=front*(1-(math.sqrt(sn*sn+.0004)-.02)**.85)
    zc=1.125-.40*vee
    for j in range(sides):
        b=2*math.pi*j/sides;c=math.cos(b);s=math.sin(b)
        x=(.555+.23*c)*sn
        y=.055-(.52+.19*c)*cs
        z=zc+.145*s-.46*rear**1.15*max(-s,0)**1.3
        vs.append((x,y,z))
    neckline.append((.555*sn,.055-.52*cs,zc+.145))
for i in range(n):
    for j in range(sides):
        fs.append((i*sides+j,((i+1)%n)*sides+j,((i+1)%n)*sides+(j+1)%sides,i*sides+(j+1)%sides))
guide_curve('Trace — continuous V neckline',neckline,True)
hood=mesh('Hood — traced neckline and back',vs,fs,teal)
active(hood)
bm=bmesh.new();bm.from_mesh(hood.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(hood.data);bm.free()
mod=hood.modifiers.new('Soft cloth folds','SMOOTH');mod.factor=.4;mod.iterations=2
apply(hood)
for p in hood.data.polygons:p.use_smooth=True

# Align facial landmarks with their height in the reference, preserving each
# mark's small offset from the curved skin rather than flattening the marks.
head=next(o for o in scene.objects if o.name.startswith('Head —'))
head_tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
for o in scene.objects:
    if o.name.startswith(('Flat dot eye','Fine curved smile')):
        for v in o.data.vertices:
            old,_,_,_=head_tree.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)))
            new,_,_,_=head_tree.ray_cast(Vector((v.co.x,-3,v.co.z+.075)),Vector((0,1,0)))
            if old is not None and new is not None:v.co.y+=new.y-old.y
            v.co.z+=.075
        o.data.update()
    elif o.name.startswith('Ear '):
        for v in o.data.vertices:v.co.z+=.075
        o.data.update()

# Thin rims retain the original dot eyes without making them protruding beads.
rim_mat=bpy.data.materials['Smile']
for eye in [o for o in scene.objects if o.name.startswith('Flat dot eye')]:
    bm=bmesh.new();bm.from_mesh(eye.data)
    indices={v.index for e in bm.edges if e.is_boundary for v in e.verts}
    pts=[eye.matrix_world@v.co for v in eye.data.vertices if v.index in indices]
    center=sum(pts,Vector())/len(pts)
    pts.sort(key=lambda p:math.atan2(p.z-center.z,p.x-center.x))
    d=bpy.data.curves.new('Eye ink rim','CURVE');d.dimensions='3D';d.bevel_depth=.0022;d.bevel_resolution=2
    s=d.splines.new('POLY');s.points.add(len(pts)-1);s.use_cyclic_u=True
    for p,co in zip(s.points,pts):p.co=(co.x,co.y-.001,co.z,1)
    o=bpy.data.objects.new('Eye ink rim',d);scene.collection.objects.link(o);d.materials.append(rim_mat);o['avatar_part']=True
    apply(o);bm.free()

# Use scanline strips following the supplied bean silhouette. Each strip has
# evenly spaced vertices, keeping the print smooth on the curved cloth without
# a dense mesh. The original image remains unchanged and supplies every pixel.
source=bpy.data.images.load(str(OUT/'bean-logo.jpg'));source.pack()
w,h=source.size
pixels=np.array(source.pixels[:],dtype=np.float32).reshape(h,w,4)
step=2;r,g,b=[pixels[::step,::step,c] for c in range(3)]
mask=((r>g*1.35)&(r>b*1.4)&(r>.4))|((r>.75)&(g>.75)&(b>.75))
ys,xs=np.nonzero(mask)
first,last=int(ys.min()),int(ys.max())
rows=[]
for j in sorted(set(range(first,last+1,3))|{last}):
    row_x=np.flatnonzero(mask[j])
    if len(row_x):rows.append((j*step,float(row_x.min()*step),float((row_x.max()+1)*step)))
minx=float(xs.min()*step);maxx=float((xs.max()+1)*step);miny=first*step
scale=1.06/(maxx-minx);center=(minx+maxx)/2;bottom=-.075
vs=[];fs=[];across=64
for row,left,right in rows:
    for i in range(across+1):
        px=left+(right-left)*i/across
        vs.append(((px-center)*scale,0,(row-miny)*scale+bottom))
for j in range(len(rows)-1):
    for i in range(across):
        a=j*(across+1)+i;b=a+across+1
        fs.extend([(a,a+1,b+1),(a,b+1,b)])
logo_mat=bpy.data.materials.new('BEAN 1833 — supplied flat artwork');logo_mat.use_nodes=True
p=logo_mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.95;p.inputs['Specular IOR Level'].default_value=0
tex=logo_mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=source
logo_mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
patch=mesh('BEAN 1833 — surface print',vs,fs,logo_mat)
bm=bmesh.new();bm.from_mesh(patch.data)
for _ in range(8):
    long_edges=[e for e in bm.edges if e.calc_length()>.025]
    if not long_edges:break
    bmesh.ops.subdivide_edges(bm,edges=long_edges,cuts=1,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,.003),plane_no=(0,0,1),clear_inner=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces))
bm.to_mesh(patch.data);bm.free()
body=next(o for o in scene.objects if o.name=='Hoodie body')
tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
for v in patch.data.vertices:
    hit,normal,_,_=tree.ray_cast(Vector((v.co.x,-3,v.co.z)),Vector((0,1,0)))
    if hit is None:raise RuntimeError('Logo extends beyond the hoodie')
    v.co.y=hit.y-.004
uv=patch.data.uv_layers.new(name='Unchanged supplied logo')
for f in patch.data.polygons:
    for loop in f.loop_indices:
        v=patch.data.vertices[patch.data.loops[loop].vertex_index].co
        uv.data[loop].uv=((v.x/scale+center)/w,((v.z-bottom)/scale+miny)/h)
# Guard against triangles sinking into the shirt after projection.
patch.data.calc_loop_triangles()
for tri in patch.data.loop_triangles:
    coords=[patch.data.vertices[i].co for i in tri.vertices]
    probes=[sum(coords,Vector())/3]+[(coords[i]+coords[(i+1)%3])/2 for i in range(3)]
    for p in probes:
        hit,_,_,_=tree.ray_cast(Vector((p.x,-3,p.z)),Vector((0,1,0)))
        if hit is not None and p.y>=hit.y:raise RuntimeError(f'Decal intersects the shirt at {tuple(p)} by {p.y-hit.y}')
for o in list(scene.objects):
    if o.name.startswith('Original cropped chest graphic'):bpy.data.objects.remove(o,do_unlink=True)

# The reference's shoulders and hood are wider relative to the skull. Apply
# the same fit to the cloth, seams, cords, and print so their alignment holds.
for o in scene.objects:
    if o.type=='MESH' and o.name.startswith(('Hood','Soft raglan','Raglan seam','BEAN')):
        for v in o.data.vertices:v.co.x*=1.08
        o.data.update()
for spline in bpy.data.objects['Trace — continuous V neckline'].data.splines:
    for p in spline.points:p.co.x*=1.08

# Pack the concept and place view-aligned image boards behind matching cameras.
concept=bpy.data.images.load(str(OUT/'concept.png'));concept.pack()
def reference_board(name,crop,camera_pos):
    target=Vector((0,0,1.72));position=Vector(camera_pos)
    rotation=(target-position).to_track_quat('-Z','Y')
    right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0));forward=rotation@Vector((0,0,-1))
    x0,y0,x1,y1=crop;ww=(x1-x0)/208;hh=(y1-y0)/208
    center=target+forward*1.8
    verts=[tuple(center+right*x*ww/2+up*y*hh/2) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage');tex.image=concept
    mat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
    board=mesh(name,verts,[(0,1,2,3)],mat,False)
    scene.collection.objects.unlink(board);refs.objects.link(board)
    coords=[(x0/1536,1-y1/1024),(x1/1536,1-y1/1024),(x1/1536,1-y0/1024),(x0/1536,1-y0/1024)]
    uv=board.data.uv_layers.new()
    for loop in board.data.loops:uv.data[loop.index].uv=coords[loop.vertex_index]
    board.hide_set(True)
    data=bpy.data.cameras.new(name+' camera');data.type='ORTHO';data.ortho_scale=4.05
    cam=bpy.data.objects.new(name+' camera',data);refs.objects.link(cam);cam.location=position;cam.rotation_euler=rotation.to_euler()
    return board
reference_board('Reference 01 — front three-quarter',(70,110,535,850),(2.45,-8,2.62))
reference_board('Reference 02 — side',(592,110,991,850),(8,0,2.62))
reference_board('Reference 03 — rear',(1030,110,1465,850),(3.4,7,2.62))

objects=[o for o in scene.objects if o.type=='MESH' and o.get('avatar_part')]
scene.cycles.samples=64;scene.render.resolution_x=800;scene.render.resolution_y=1000
cam=scene.camera;cam.data.ortho_scale=4.05
views=[('front',(0,-8,2.62)),('three-quarter',(2.45,-8,2.62)),('side',(8,0,2.62)),('other-side',(-8,0,2.62)),('rear',(3.4,7,2.62))]
for name,pos in views:
    cam.location=pos;cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'{name}.png');bpy.ops.render.render(write_still=True)
cam.location=views[1][1];cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=None
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'avatar-v4.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
export_path=OUT/'avatar-v4.glb' if os.environ.get('AVATAR_DRAFT') else ROOT/'public/models/avatar.glb'
bpy.ops.export_scene.gltf(filepath=str(export_path),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
print('Exported',export_path,flush=True)
