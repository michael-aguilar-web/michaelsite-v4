"""Render three views of the saved model in one Blender scene."""
from pathlib import Path
import bpy
import math, sys
from mathutils import Matrix, Vector

root=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
version=args[0] if args else 'v5'
bpy.ops.wm.open_mainfile(filepath=str(root/f'artwork/avatar/avatar-{version}.blend'))
scene=bpy.context.scene
models=[o for o in scene.objects if o.type=='MESH' and o.get('avatar_part')]
for x,angle in [(-2.48,-17),(0,-80),(2.48,-206)]:
    transform=Matrix.Translation((x,0,0)) @ Matrix.Rotation(math.radians(angle),4,'Z')
    for original in models:
        instance=original.copy()
        instance.data=original.data
        scene.collection.objects.link(instance)
        instance.matrix_world=transform @ original.matrix_world
for original in models:original.hide_render=True
camera=scene.camera
camera.location=(0,-12,2.91)
camera.rotation_euler=(Vector((0,0,1.72))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=8.0
scene.render.resolution_x=1600
scene.render.resolution_y=840
scene.render.filepath=str(root/f'artwork/avatar/turnaround-{version}.png')
for o in scene.objects:
    if o.type=='LIGHT':
        o.data.size=7
        o.data.energy*=1.45
bpy.ops.render.render(write_still=True)
