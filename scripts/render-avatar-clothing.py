"""Render a close view of the garment every 15 degrees around the avatar."""
from pathlib import Path
import bpy,math,sys
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'v11'
angle_option=next((a for a in args[1:] if a.startswith('--angles=')),None)
angles=[int(a)%360 for a in angle_option.split('=',1)[1].split(',')] if angle_option else list(range(0,360,15))
bpy.ops.wm.open_mainfile(filepath=str(ART/f'avatar-{version}.blend'))
scene=bpy.context.scene;cam=scene.camera
out=ART/'validation'/f'{version}-clothing';out.mkdir(parents=True,exist_ok=True)
scene.render.resolution_x=512;scene.render.resolution_y=360;scene.render.resolution_percentage=100
scene.cycles.samples=48;scene.cycles.use_denoising=True
cam.data.type='ORTHO';cam.data.ortho_scale=2.5
for angle in angles:
    yaw=math.radians(angle);elev=math.radians(6)
    direction=Vector((math.sin(yaw)*math.cos(elev),-math.cos(yaw)*math.cos(elev),math.sin(elev)))
    cam.location=Vector((0,0,.67))+direction*8
    cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    for name,position in [('Softbox above left',(-3,-4,6)),('Soft front fill',(3,-4,3)),('Soft rim',(1,3,5))]:
        light=bpy.data.objects[name];light.location=Matrix.Rotation(yaw,4,'Z')@Vector(position)
        light.rotation_euler=(Vector((0,0,1.7))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/f'orbit-{angle:03d}.png')
    bpy.ops.render.render(write_still=True)
print(f'Finished {len(angles)} garment views:',out,flush=True)
