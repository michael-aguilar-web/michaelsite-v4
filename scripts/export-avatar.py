"""Check and export a reviewed avatar scene to a local draft GLB."""
from pathlib import Path
import bpy, bmesh, json, math, sys
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'v5'
bpy.ops.wm.open_mainfile(filepath=str(ART/f'avatar-{version}.blend'))
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=='MESH' and o.get('avatar_part')]
report={'objects':len(objects),'vertices':0,'triangles':0,'hair':{}}
all_vertices=[]
for obj in objects:
    coords=np.array([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
    if not np.isfinite(coords).all():raise RuntimeError(f'Invalid vertices in {obj.name}')
    all_vertices.extend(coords)
    obj.data.calc_loop_triangles()
    report['vertices']+=len(coords);report['triangles']+=len(obj.data.loop_triangles)
    if obj.name.startswith('Hair'):
        bm=bmesh.new();bm.from_mesh(obj.data)
        boundary=sum(e.is_boundary for e in bm.edges)
        nonmanifold=sum(not e.is_manifold for e in bm.edges)
        remaining=set(bm.verts);components=[]
        while remaining:
            seed=remaining.pop();stack=[seed];count=0
            while stack:
                v=stack.pop();count+=1
                for e in v.link_edges:
                    other=e.other_vert(v)
                    if other in remaining:remaining.remove(other);stack.append(other)
            components.append(count)
        report['hair']={'boundaryEdges':boundary,'nonmanifoldEdges':nonmanifold,'componentVertices':sorted(components,reverse=True)}
        bm.free()
        if boundary or nonmanifold:raise RuntimeError('Hair mesh is not closed')
        if sum(n>30 for n in components)>1:raise RuntimeError('Hair has disconnected pieces')
all_vertices=np.array(all_vertices)
report['bounds']={'min':all_vertices.min(axis=0).tolist(),'max':all_vertices.max(axis=0).tolist()}

# Open the editable file at a useful portrait camera, without reference boards.
yaw=math.radians(17);elev=math.radians(6)
back=Vector((math.sin(yaw)*math.cos(elev),-math.cos(yaw)*math.cos(elev),math.sin(elev)))
cam=scene.camera;cam.location=Vector((0,0,1.72))+back*8
cam.rotation_euler=(-back).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=4.05
scene.render.resolution_x=800;scene.render.resolution_y=1000
for name,pos in [('Softbox above left',(-3,-4,6)),('Soft front fill',(3,-4,3)),('Soft rim',(1,3,5))]:
    light=bpy.data.objects[name];light.location=Matrix.Rotation(yaw,4,'Z')@Vector(pos)
    light.rotation_euler=(Vector((0,0,1.7))-light.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/f'avatar-{version}.blend'))
for obj in objects:obj.select_set(True)
target=ART/f'avatar-{version}.glb'
bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
report['glbBytes']=target.stat().st_size
(ART/f'validation/export-{version}.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
