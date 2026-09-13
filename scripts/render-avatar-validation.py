"""Render the avatar using the same frozen cameras for every model version."""
from pathlib import Path
import bpy, json, math, sys
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'v5'
bpy.ops.wm.open_mainfile(filepath=str(ART/f'avatar-{version}.blend'))
scene=bpy.context.scene
out=ART/'validation'/f'{version}-calibrated';out.mkdir(parents=True,exist_ok=True)
cameras=json.loads((ART/'validation/calibrated-cameras.json').read_text())
cam=scene.camera;cam.data.type='ORTHO'
scene.render.resolution_y=740;scene.render.resolution_percentage=100
scene.cycles.samples=48;scene.cycles.use_denoising=True
widths={'three-quarter':470,'side':399,'rear':435}
angle_arg=next((arg for arg in args if arg.startswith(('--angles=','--extra-angles='))),None)
if angle_arg:
    angles=[int(angle) for angle in angle_arg.split('=',1)[1].split(',')]
    extra={f'orbit-{angle:03d}':[angle,6,1,0,-10] for angle in angles}
    if angle_arg.startswith('--extra-'): cameras.update(extra)
    else: cameras=extra
    widths.update({name:470 for name in extra})
if '--rotation' in args:
    orbit={f'orbit-{angle:03d}':[angle,6,1,0,-10] for angle in range(0,360,45)}
    cameras.update(orbit)
    widths.update({name:470 for name in orbit})
for name,(yaw,elev,scale,dx,dy) in cameras.items():
    a,b=map(math.radians,[yaw,elev])
    back=Vector((math.sin(a)*math.cos(b),-math.cos(a)*math.cos(b),math.sin(b)))
    right=Vector((math.cos(a),math.sin(a),0));up=back.cross(right)
    center=Vector((0,0,1.72))-right*dx/(208*scale)+up*dy/(208*scale)
    cam.location=center+back*8
    cam.rotation_euler=(-back).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=740/(208*scale)
    # Each reference image uses a portrait studio setup. Move the light rig
    # with the comparison camera, just as the fixed camera sees a turntable.
    rotation=Matrix.Rotation(a,4,'Z')
    for light_name,position in [('Softbox above left',(-3,-4,6)),('Soft front fill',(3,-4,3)),('Soft rim',(1,3,5))]:
        light=bpy.data.objects[light_name];light.location=rotation@Vector(position)
        light.rotation_euler=(Vector((0,0,1.7))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=widths[name]
    scene.render.filepath=str(out/f'{name}.png')
    bpy.ops.render.render(write_still=True)
# Export precisely the geometry that was rendered for the independent mask fit.
import numpy as np
vertices=[];triangles=[];labels=[];offset=0;parts={}
for obj in scene.objects:
    if obj.type!='MESH' or not obj.get('avatar_part'):continue
    obj.data.calc_loop_triangles()
    vs=np.array([tuple(obj.matrix_world@v.co) for v in obj.data.vertices],np.float32)
    fs=np.array([tuple(t.vertices) for t in obj.data.loop_triangles],np.int32)+offset
    parts[obj.name]=[offset,offset+len(vs)];offset+=len(vs)
    vertices.extend(vs);triangles.extend(fs)
    label=1 if obj.name.startswith('Hair') else 2 if obj.name.startswith(('Head','Ear','Flat','Fine','Eye')) else 3
    labels.extend([label]*len(fs))
np.savez_compressed(out/'geometry.npz',vertices=np.array(vertices),triangles=np.array(triangles),labels=np.array(labels))
(out/'parts.json').write_text(json.dumps(parts,indent=2))
print('Finished calibrated validation renders:',out,flush=True)
