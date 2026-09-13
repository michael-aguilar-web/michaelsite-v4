"""Refine the hair in v7, keeping the accepted v6 save point unchanged."""
from pathlib import Path
import bpy, bmesh, runpy, sys, math

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artwork/avatar'
cleanup_only='--cleanup' in sys.argv
polish_only='--polish' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(ART/('avatar-v7.blend' if cleanup_only or polish_only else 'avatar-v6.blend')))
if not cleanup_only and not polish_only:runpy.run_path(str(ROOT/'scripts/avatar-hair-v7.py'))
hair=bpy.data.objects['Hair — reference silhouette surface']
if not cleanup_only:
    def ease(a,b,x):
        t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
    group=hair.vertex_groups.new(name='Round the swept side connection')
    for v in hair.data.vertices:
        x,y,z=v.co;angle=math.atan2(x,-(y+.025))
        weight=math.exp(-.5*((angle+math.radians(78))/math.radians(27))**2)*ease(2.18,2.40,z)
        if weight>.001:group.add([v.index],weight,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');hair.select_set(True);bpy.context.view_layer.objects.active=hair
    mod=hair.modifiers.new('Blend the swept side roots','SMOOTH');mod.factor=.8;mod.iterations=42;mod.vertex_group=group.name
    bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(hair.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
remaining=set(bm.verts);components=[]
while remaining:
    seed=remaining.pop();stack=[seed];component=[seed]
    while stack:
        v=stack.pop()
        for edge in v.link_edges:
            other=edge.other_vert(v)
            if other in remaining:
                remaining.remove(other);stack.append(other);component.append(other)
    components.append(component)
components.sort(key=len,reverse=True)
if any(len(c)>30 for c in components[1:]):raise RuntimeError('A hair lock is disconnected from the main cap')
for component in components[1:]:bmesh.ops.delete(bm,geom=component,context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(hair.data);bm.free()
hair.data.validate(clean_customdata=True);hair.data.update()
for f in hair.data.polygons:f.use_smooth=True
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v7.blend'))
print('Saved hair refinement as avatar-v7.blend; v6 unchanged.', flush=True)
