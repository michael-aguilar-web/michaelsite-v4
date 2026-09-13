"""Build the avatar with Blender's Python API; render before publishing the GLB.

    Blender --background --python scripts/build-avatar.py
    AVATAR_DRAFT=1 skips the public asset export while refining the artwork.

Coordinates: front is -Y, up is Z. Dimensions are artistic, in Blender units.
"""
import bpy
import math
import os
from pathlib import Path
from mathutils import Vector
import numpy as np
import bmesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artwork/avatar'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4


def material(name, rgb, roughness=.88):
    color = tuple(linear(int(rgb[i:i + 2], 16) / 255) for i in (0, 2, 4))
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Specular IOR Level'].default_value = .16
    return m


skin = material('Peach skin', 'F2A574')
hair = material('Ink black hair', '202120', .96)
ink = material('Warm brown eyes', '58342B')
mouth_mat = material('Smile', '34241F')
teal = material('Teal hoodie', '1595AB')
inside = material('Hood lining', '064852')
seam = material('Teal seam', '118497')
cord = material('Warm white drawstrings', 'E3E6E2')


def mesh(name, vs, fs, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vs, [], fs)
    data.update()
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    for f in data.polygons:
        f.use_smooth = True
    return o


def active(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply(o):
    active(o)
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def uv(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def curve(name, pts, radius, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    data.resolution_u = 20
    s = data.splines.new('BEZIER')
    s.bezier_points.add(len(pts) - 1)
    for b, p in zip(s.bezier_points, pts):
        b.co = p
        b.handle_left_type = 'AUTO'
        b.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def smooth_profile(points, steps=5):
    # Cardinal spline with restrained tangents keeps the neck/chin continuous.
    out = []
    for i in range(len(points) - 1):
        p0 = Vector(points[max(0, i - 1)])
        p1 = Vector(points[i])
        p2 = Vector(points[i + 1])
        p3 = Vector(points[min(len(points) - 1, i + 2)])
        for j in range(steps):
            t = j / steps
            m1 = (p2 - p0) * .4
            m2 = (p3 - p1) * .4
            out.append(tuple((2*t**3-3*t*t+1)*p1 + (t**3-2*t*t+t)*m1 + (-2*t**3+3*t*t)*p2 + (t**3-t*t)*m2))
    out.append(points[-1])
    return out


def rings(name, profile, mat, exponent=2, n=64):
    vs, fs = [], []
    for z, rx, ry, cy, cx in profile:
        for i in range(n):
            a = 2*math.pi*i/n
            sn, cs = math.sin(a), math.cos(a)
            front_drop=.25*max(cs,0)**4*max(0,(z-.72)/.34) if name=='Hoodie body' else 0
            vs.append((cx+rx*math.copysign(abs(sn)**(2/exponent), sn), cy-ry*math.copysign(abs(cs)**(2/exponent), cs), z-front_drop))
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*n+i; b=j*n+(i+1)%n
            fs.append((a,b,b+n,a+n))
    fs.append(tuple(reversed(range(n))))
    fs.append(tuple((len(profile)-1)*n+i for i in range(n)))
    return mesh(name, vs, fs, mat)


head_profile = smooth_profile([
    (.79,.255,.23,.015,0), (1.01,.267,.245,.015,0),
    (1.14,.268,.25,.02,0), (1.23,.29,.275,.02,0),
    (1.31,.35,.32,.023,0), (1.42,.48,.394,.025,0),
    (1.56,.63,.477,.024,0), (1.74,.75,.55,.015,0),
    (1.94,.823,.591,.008,0), (2.15,.853,.614,.012,0), (2.36,.838,.61,.02,0),
    (2.48,.82,.604,.03,0), (2.70,.73,.55,.04,0),
    (2.92,.51,.40,.05,0), (3.055,.14,.14,.05,0), (3.069,.002,.002,.05,0)
])
head = rings('Head — continuous cheeks, jaw and neck', head_profile, skin, 2.12)


def profile_at(profile, z):
    for a,b in zip(profile, profile[1:]):
        if a[0] <= z <= b[0]:
            t=(z-a[0])/(b[0]-a[0])
            return tuple(x+(y-x)*t for x,y in zip(a,b))
    return profile[0] if z < profile[0][0] else profile[-1]


def surface_y(profile, x, z, exponent=2):
    _,rx,ry,cy,cx=profile_at(profile,z)
    return cy-ry*max(0,1-(abs(x-cx)/rx)**exponent)**(1/exponent)


for side in [-1,1]:
    ear=uv('Ear L' if side<0 else 'Ear R', (side*.862,-.008,2.015),(.155,.148,.209),skin)
    ear.rotation_euler.y=side*-.15

# Face marks lie directly on the skin, rather than sticking out like beads.
def eye(x):
    vs=[(x,surface_y(head_profile,x,2.012,2.12)-.003,2.012)]
    fs=[]; n=64
    for j in range(1,5):
        r=j/4
        for i in range(n):
            a=2*math.pi*i/n
            xx=x+.047*r*math.cos(a); z=2.012+.055*r*math.sin(a)
            vs.append((xx,surface_y(head_profile,xx,z,2.12)-.003-.004*(1-r*r),z))
    for i in range(n): fs.append((0,1+i,1+(i+1)%n))
    for j in range(3):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;fs.append((a,a+n,b+n,b))
    return mesh('Flat dot eye',vs,fs,ink)
for x in [-.316,.316]: eye(x)
smile=[]
for i in range(17):
    t=i/16; x=-.18+.36*t; z=1.841+.033*(2*t-1)**2+.009*t
    smile.append((x,surface_y(head_profile,x,z,2.12)-.005,z))
curve('Fine curved smile',smile,.005,mouth_mat)

# Scalp and forelocks are closed volumes, merged into one soft silhouette.
hair_parts=[]
vs=[];fs=[];n=128;rows=36
for j in range(rows+1):
    t=j/rows
    for i in range(n):
        a=-math.pi+2*math.pi*i/n
        front=max(math.cos(a),0)
        back=max(-math.cos(a),0)
        boundary=2.29+.47*front**3-.49*back**1.2
        phi=.003+(math.acos((boundary-2.33)/.87)-.003)*t
        # Crown is broader and slightly swept to the left.
        x=.91*math.sin(phi)*math.sin(a)-.045*(1-t)**2
        y=.065-.665*math.sin(phi)*math.cos(a)
        z=2.33+.87*math.cos(phi)
        vs.append((x,y,z))
for j in range(rows):
    for i in range(n):
        a=j*n+i;b=j*n+(i+1)%n;fs.append((a,a+n,b+n,b))
vs.append((0,.08,2.36));center=len(vs)-1
for i in range(n):fs.append((rows*n+i,center,rows*n+(i+1)%n))
hair_parts.append(mesh('Scalp volume',vs,fs,hair))


def bezier_outline(segments, samples=12):
    out=[]
    for p0,p1,p2,p3 in segments:
        for i in range(samples):
            t=i/samples
            out.append(tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for a,b,c,d in zip(p0,p1,p2,p3)))
    return out


def pillow(name, outline, center, surface, bulge=.12, depth=.12, rings_n=18, edge_depth=0):
    vs=[];fs=[];n=len(outline)
    # Front and back disks with a rounded shared perimeter.
    for back in (False,True):
        for j in range(rings_n+1):
            r=.0001+(1-.0001)*j/rings_n
            for xx,zz in outline:
                x=center[0]+r*(xx-center[0]);z=center[1]+r*(zz-center[1])
                base=surface(x,z)
                y=base + (depth if back else -bulge)*math.sqrt(max(0,1-r*r))
                if back:y+=edge_depth*max(0,min(1,(z-2.80)/.4))
                vs.append((x,y,z))
    off=(rings_n+1)*n
    for j in range(rings_n):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n
            fs.append((a,b,b+n,a+n))
            fs.append((off+a,off+a+n,off+b+n,off+b))
    for i in range(n):
        a=rings_n*n+i;b=rings_n*n+(i+1)%n
        fs.append((a,off+a,off+b,b))
    fs.append(tuple(reversed(range(n))))
    fs.append(tuple(off+i for i in range(n)))
    return mesh(name,vs,fs,hair)


def forehead(x,z):
    return .03-.70*math.sqrt(max(.12,1-(x/1.02)**2-((z-2.43)/1.04)**2))

# Swept forelock: broad arc ending in two curved, tapered lobes.
outline=bezier_outline([
    ((-.855,3.10),(-.64,3.255),(-.16,3.285),(.24,3.13)),
    ((.24,3.13),(.39,3.02),(.40,2.79),(.20,2.586)),
    ((.20,2.586),(-.02,2.45),(-.34,2.378),(-.61,2.352)),
    ((-.61,2.352),(-.65,2.343),(-.59,2.472),(-.572,2.51)),
    ((-.572,2.51),(-.69,2.324),(-.82,2.253),(-.899,2.26)),
    ((-.899,2.26),(-1.031,2.32),(-1.003,2.794),(-.86,2.97)),
    ((-.86,2.97),(-.828,3.018),(-.74,3.056),(-.855,3.10)),
])
hair_parts.append(pillow('Broad swept forelock',outline,(-.29,2.78),forehead,.10,.40,edge_depth=.28))
# Right lobe curls toward the ear, with one fine pointed strand at its part.
outline=bezier_outline([
    ((.20,3.115),(.43,3.19),(.74,3.05),(.865,2.86)),
    ((.865,2.86),(.975,2.68),(.927,2.38),(.816,2.25)),
    ((.816,2.25),(.791,2.234),(.738,2.30),(.696,2.38)),
    ((.696,2.38),(.688,2.345),(.718,2.292),(.715,2.277)),
    ((.715,2.277),(.491,2.403),(.395,2.533),(.298,2.68)),
    ((.298,2.68),(.295,2.57),(.329,2.483),(.355,2.404)),
    ((.355,2.404),(.318,2.39),(.163,2.584),(.14,2.701)),
    ((.14,2.701),(.099,2.874),(.121,3.023),(.20,3.115)),
])
hair_parts.append(pillow('Temple sweep and fine fringe',outline,(.53,2.78),lambda x,z:forehead(x,z)-.008,.075,.40,edge_depth=.28))

# Blend the elevated front sweep into the crown before sculpting the tufts.
hair_parts.append(uv('Crown transition',(-.16,-.11,2.965),(.65,.43,.277),hair))

# Curved flattened tufts use perpendicular elliptical sections, not hollow caps.
def tuft(name, control, width, thickness):
    vs=[];fs=[];segments=32;sides=24
    p0,p1,p2,p3=map(Vector,control)
    for j in range(segments+1):
        t=j/segments
        center=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
        tangent=(3*(1-t)**2*(p1-p0)+6*(1-t)*t*(p2-p1)+3*t*t*(p3-p2)).normalized()
        normal=Vector((tangent.z,0,-tangent.x)).normalized()
        taper=max(.001,(1-t)**.72)
        for i in range(sides):
            angle=2*math.pi*i/sides
            v=center+normal*(width*taper*math.cos(angle))+Vector((0,thickness*taper*math.sin(angle),0))
            vs.append(tuple(v))
    for j in range(segments):
        for i in range(sides):
            a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs.append(tuple(reversed(range(sides))))
    fs.append(tuple(segments*sides+i for i in range(sides)))
    return mesh(name,vs,fs,hair)
hair_parts.append(tuft('Tall curved tuft',[(.295,.055,3.095),(.359,.055,3.20),(.293,.055,3.337),(.217,.055,3.402)],.114,.048))
hair_parts.append(tuft('Short curved tuft',[(.433,.075,3.07),(.476,.075,3.17),(.571,.075,3.263),(.642,.075,3.248)],.077,.037))

# Voxel union erases primitive joins while retaining sculpted lobe shapes.
bpy.ops.object.select_all(action='DESELECT')
for o in hair_parts:o.select_set(True)
bpy.context.view_layer.objects.active=hair_parts[0]
bpy.ops.object.join()
o=bpy.context.object;o.name='Hair — sculpted swept silhouette'
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
o.data.remesh_voxel_size=.012
bpy.ops.object.voxel_remesh()
mod=o.modifiers.new('Soften sculpt surface','SMOOTH');mod.factor=.8;mod.iterations=12
mod=o.modifiers.new('Web topology','DECIMATE');mod.ratio=.30
apply(o)
for p in o.data.polygons:p.use_smooth=True

# Gently taper the torso into sloped shoulders; sleeves are shaped around it.
body_profile=smooth_profile([
    (0,.827,.414,.045,0),(.018,.827,.414,.045,0),
    (.30,.805,.427,.043,0),(.58,.756,.406,.04,0),
    (.82,.668,.363,.046,0),(1.015,.471,.29,.058,0),
    (1.06,.32,.25,.065,0)
])
rings('Hoodie body',body_profile,teal,2.2)
for side in [-1,1]:
    profile=smooth_profile([
        (0,.194,.335,.035,side*.827),(.018,.194,.335,.035,side*.827),
        (.22,.184,.333,.04,side*.803),(.49,.167,.30,.035,side*.762),
        (.71,.15,.26,.043,side*.692),(.88,.125,.19,.045,side*.596),
        (.954,.015,.06,.05,side*.515)
    ])
    rings('Soft raglan sleeve',profile,teal,2.08,64)
    # Recessed-looking seam is a thin tonal curve, rather than a deep channel.
    curve('Raglan seam',[(side*.45,-.242,.974),(side*.61,-.266,.848),(side*.66,-.301,.67),(side*.67,-.32,.40),(side*.685,-.33,.02)],.0035,seam)

# The collar is an oval fabric roll: wide at the shoulders, narrow at the V.
# Its cross-section is fully rounded so the outer edge cannot form a sharp lip.
vs=[];fs=[];n=128;cross=36
for i in range(n):
    a=2*math.pi*i/n;cs=math.cos(a);sn=math.sin(a)
    front=max(cs,0)**3
    zc=1.09-.275*front
    for j in range(cross):
        b=2*math.pi*j/cross;c=math.cos(b)
        x=(.567+.22*c)*sn
        y=.035-(.337+.101*c)*cs
        z=zc+.125*math.sin(b)-.018*c
        vs.append((x,y,z))
for i in range(n):
    for j in range(cross):
        fs.append((i*cross+j,((i+1)%n)*cross+j,((i+1)%n)*cross+(j+1)%cross,i*cross+(j+1)%cross))
collar=mesh('Rounded folded collar',vs,fs,teal)
hood_outline=bezier_outline([
    ((-.685,1.115),(-.53,1.218),(-.23,1.205),(0,1.177)),
    ((0,1.177),(.23,1.205),(.53,1.218),(.685,1.115)),
    ((.685,1.115),(.779,.871),(.442,.643),(0,.518)),
    ((0,.518),(-.442,.643),(-.779,.871),(-.685,1.115)),
],24)
hood=pillow('Draped hood',hood_outline,(0,.925),lambda x,z:.305,-.324,-.16,22)
hood.data.materials.clear();hood.data.materials.append(teal)
active(collar);hood.select_set(True);bpy.ops.object.join()
o=bpy.context.object;o.name='Hood — folded collar and tapered back'
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
o.data.remesh_voxel_size=.012;bpy.ops.object.voxel_remesh()
mod=o.modifiers.new('Soft cloth transitions','SMOOTH');mod.factor=.7;mod.iterations=8
mod=o.modifiers.new('Web topology','DECIMATE');mod.ratio=.32
apply(o)
for f in o.data.polygons:f.use_smooth=True

# Strings lie on the chest, with slightly different curves and flat cropped ends.
for side in [-1,1]:
    coords=[(side*.222,.691),(side*.245,.601),(side*.274,.413),(side*(.296 if side<0 else .276),.20),(side*(.314 if side<0 else .278),.0)]
    pts=[(x,surface_y(body_profile,x,z,2.2)-.043,z) for x,z in coords]
    curve('Hood drawstring',pts,.038,cord)

# Reuse the real chest artwork as a UV decal. The PNG is sampled directly,
# without inventing replacement lettering or painting a new texture.
source=bpy.data.images.load(str(ROOT/'src/assets/branding/s3_1white_cropped.png'))
source.pack()
w,h=source.size
pixels=np.array(source.pixels[:],dtype=np.float32).reshape(h,w,4)
red_mask=(pixels[:int(h*.15),:,0]>.55)&(pixels[:int(h*.15),:,1]<.4)&(pixels[:int(h*.15),:,2]<.35)
rows=[]
for row in range(red_mask.shape[0]):
    xs=np.flatnonzero(red_mask[row])
    xs=xs[(xs>w*.32)&(xs<w*.69)]
    if len(xs)>2 and row%2==0:rows.append((row,int(xs.min()),int(xs.max())))
logo=bpy.data.materials.new('Original chest illustration');logo.use_nodes=True
p=logo.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.95;p.inputs['Specular IOR Level'].default_value=0
tex=logo.node_tree.nodes.new('ShaderNodeTexImage');tex.image=source
logo.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
vs=[];fs=[];uvs=[];across=32
for row,left,right in rows:
    for i in range(across+1):
        px=left+(right-left)*i/across
        x=(px-w*.496)*.00435;z=row*.00435+.001
        vs.append((x,surface_y(body_profile,x,z,2.2)-.003,z))
        uvs.append((px/w,row/h))
for j in range(len(rows)-1):
    for i in range(across):
        a=j*(across+1)+i;fs.append((a,a+1,a+across+2,a+across+1))
decal=mesh('Original cropped chest graphic',vs,fs,logo)
uv_layer=decal.data.uv_layers.new(name='Original illustration UV')
for poly in decal.data.polygons:
    for loop_idx in poly.loop_indices:
        uv_layer.data[loop_idx].uv=uvs[decal.data.loops[loop_idx].vertex_index]

# Retain editable objects and materials in the saved scene.
for o in list(bpy.context.scene.objects):
    if o.type in {'MESH','CURVE','FONT'}:apply(o)
avatar=list(bpy.context.scene.objects)

scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.render.film_transparent=False
scene.world.use_nodes=True
nodes=scene.world.node_tree.nodes;nodes.clear()
out=nodes.new('ShaderNodeOutputWorld');bg=nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(1,1,1,1)
light_path=nodes.new('ShaderNodeLightPath');mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
mix.inputs[1].default_value=(.38,.38,.38,1);mix.inputs[2].default_value=(1,1,1,1)
scene.world.node_tree.links.new(light_path.outputs['Is Camera Ray'],mix.inputs[0])
scene.world.node_tree.links.new(mix.outputs[0],bg.inputs['Color'])
scene.world.node_tree.links.new(bg.outputs[0],out.inputs[0])


def area(name,loc,power,size):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(Vector((0,0,1.7))-o.location).to_track_quat('-Z','Y').to_euler()
area('Softbox above left',(-3,-4,6),320,5)
area('Soft front fill',(3,-4,3),125,4)
area('Soft rim',(1,3,5),150,4)
bpy.ops.object.camera_add(location=(0,-8,2.5))
cam=bpy.context.object;cam.name='Avatar portrait camera';cam.data.type='ORTHO';cam.data.ortho_scale=4.05;scene.camera=cam
views=[('front',(0,-8,2.62)),('three-quarter',(2.45,-8,2.62)),('side',(8,-.1,2.62)),('rear',(3.4,7,2.62))]
for name,pos in views:
    cam.location=pos
    cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'{name}.png')
    bpy.ops.render.render(write_still=True)
cam.location=views[1][1];cam.rotation_euler=(Vector((0,0,1.73))-cam.location).to_track_quat('-Z','Y').to_euler()
# Opening the file shows the same portrait camera and material colors.
for screen in bpy.data.screens:
    for area_ in screen.areas:
        if area_.type=='VIEW_3D':
            area_.spaces.active.region_3d.view_perspective='CAMERA'
            area_.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'avatar-v2.blend'))
export_path=OUT/'avatar-v2.glb' if os.environ.get('AVATAR_DRAFT') else ROOT/'public/models/avatar.glb'
bpy.ops.object.select_all(action='DESELECT')
for o in avatar:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(export_path),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
print('Avatar exported:',sum(len(o.data.polygons) for o in avatar),'polygons;',export_path)
for o in avatar:print(o.name,len(o.data.polygons))
