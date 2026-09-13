"""Refine v7's hidden side/rear surfaces while locking its approved front.

Always starts from the saved v7. The front-facing vertices and a geodesic
margin are fixed; no topology, clothing, facial marks, or ears are changed.
"""
from pathlib import Path
import bpy, json, math, heapq
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART / 'avatar-v7.blend'))

# Visibility uses the complete avatar. A ray through a gap in the fringe must
# stop at the face, not incorrectly protect hair on the far side of the head.
scene_vertices, scene_faces = [], []
for part in bpy.context.scene.objects:
    if part.type != 'MESH' or not part.get('avatar_part'): continue
    offset = len(scene_vertices)
    scene_vertices.extend([tuple(part.matrix_world@v.co) for v in part.data.vertices])
    scene_faces.extend([tuple(offset+i for i in f.vertices) for f in part.data.polygons])
front_tree = BVHTree.FromPolygons(scene_vertices, scene_faces)


def ease(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def front_protection(obj):
    """Protect both the straight-on face and the approved portrait camera."""
    coords = np.array([tuple(v.co) for v in obj.data.vertices])
    protected = np.zeros(len(coords), dtype=bool)
    for yaw in (0, 17):
        a, b = math.radians(yaw), math.radians(6)
        direction = Vector((math.sin(a)*math.cos(b), -math.cos(a)*math.cos(b), math.sin(b)))
        for i, v in enumerate(obj.data.vertices):
            position = obj.matrix_world@v.co
            hit, normal, face, distance = front_tree.ray_cast(position+direction*5, -direction, 5.04)
            if hit is not None and (hit-position).length < .014:
                protected[i] = True
    # Preserve a generous, smoothly fading band around every protected vertex.
    adjacency = [[] for _ in coords]
    for e in obj.data.edges:
        i, j = e.vertices
        length = float(np.linalg.norm(coords[i]-coords[j]))
        adjacency[i].append((j, length)); adjacency[j].append((i, length))
    distance = np.full(len(coords), np.inf)
    distance[protected] = 0
    queue = [(0., int(i)) for i in np.flatnonzero(protected)]
    heapq.heapify(queue)
    while queue:
        d, i = heapq.heappop(queue)
        if d != distance[i]: continue
        for j, length in adjacency[i]:
            candidate = d+length
            if candidate < distance[j]:
                distance[j] = candidate; heapq.heappush(queue, (candidate, j))
    margin = ease(0., .08, distance) if obj.name.startswith('Hair') else ease(.035, .22, distance)
    return coords, protected, margin


def smooth(obj, weights, iterations, label):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    group = obj.vertex_groups.new(name=label)
    for i in np.flatnonzero(weights > 0): group.add([int(i)], float(weights[i]), 'REPLACE')
    modifier = obj.modifiers.new(label, 'SMOOTH')
    modifier.factor = .75; modifier.iterations = iterations; modifier.vertex_group = group.name
    group_name = group.name
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.vertex_groups.remove(obj.vertex_groups[group_name])


report = {}
for name, iterations in [('Head — continuous cheeks, jaw and neck', 150),
                         ('Hair — reference silhouette surface', 170)]:
    obj = bpy.data.objects[name]
    original, protected, weights = front_protection(obj)
    free_weights = weights.copy()
    x, y, z = original.T
    if name.startswith('Head'):
        # Round the transition behind the ears into the neck, tapering out well
        # above the collar and before the crown. Visible cheeks stay fixed.
        weights *= ease(1.16, 1.48, z)*(1-ease(2.42, 2.76, z))
    else:
        # Keep the cowlicks intact and soften the cap, roots, and nape only.
        weights *= (1-ease(3.10, 3.26, z))*(.12+.88*ease(2.18, 2.52, z))
    smooth(obj, weights, iterations, 'Rear fairing with the front locked')
    if name.startswith('Hair'):
        # Carry the hairline with the smoothed skull, interpolating the same
        # deformation across both sides of the shell to retain its thickness.
        head_tree = BVHTree.FromPolygons(head_before.tolist(), head_faces.tolist(), all_triangles=True)
        for i, vertex in enumerate(obj.data.vertices):
            x, y, z = vertex.co
            weight = float(free_weights[i]*ease(-.26, .06, y)*(1-ease(2.12, 2.65, z)))
            if weight <= 0: continue
            hit, normal, face, distance = head_tree.find_nearest(vertex.co)
            if hit is None: continue
            ids = head_faces[face]
            before = [Vector(head_before[j]) for j in ids]
            after = [Vector(head_after[j]) for j in ids]
            mapped = barycentric_transform(hit, *before, *after)
            vertex.co += (mapped-hit)*(weight*float(1-ease(.18, .48, distance)))
        # Continue the short hair behind the ear into the nape. The old rim
        # curled away too early, exposing a small scalp lobe in profile.
        # Slide it along the skull, preserving its existing radial clearance.
        head_now = BVHTree.FromPolygons(head_after.tolist(), head_faces.tolist(), all_triangles=True)
        heights = np.linspace(1.35, 2.65, 150)
        centers = np.array([(head_after[abs(head_after[:,2]-z)<.04,1].min()
                           +head_after[abs(head_after[:,2]-z)<.04,1].max())/2 for z in heights])
        for i, vertex in enumerate(obj.data.vertices):
            x, y, z = vertex.co
            angle = abs(math.atan2(x, -(y+.025)))
            strength = math.exp(-.5*((angle-math.radians(112))/math.radians(22))**2)
            strength *= float(free_weights[i]*(1-ease(2.12, 2.58, z))*ease(1.54, 1.85, z))
            dz = -.13*strength
            if abs(dz) < 1e-6: continue
            origin = Vector((0, float(np.interp(z, heights, centers)), z))
            direction = (vertex.co-origin).normalized()
            old, _, _, _ = head_now.ray_cast(origin, direction)
            new_origin = Vector((0, float(np.interp(z+dz, heights, centers)), z+dz))
            new, _, _, _ = head_now.ray_cast(new_origin, direction)
            if old is not None and new is not None:
                vertex.co += new-old
        coords = np.array([tuple(v.co) for v in obj.data.vertices])
        x, y, z = coords.T
        angles = np.abs(np.arctan2(x, -(y+.025)))
        blend = np.exp(-.5*((angles-math.radians(112))/math.radians(25))**2)
        blend *= free_weights*ease(1.62, 1.90, z)*(1-ease(2.53, 2.80, z))
        smooth(obj, blend, 70, 'Round the ear-to-nape transition')
    result = np.array([tuple(v.co) for v in obj.data.vertices])
    assert np.array_equal(result[protected], original[protected]), 'Front geometry changed'
    delta = np.linalg.norm(result-original, axis=1)
    report[name] = {'protectedVertices': int(protected.sum()), 'movedVertices': int((delta > 1e-7).sum()),
                    'maxDisplacement': float(delta.max()), 'frontMaxDisplacement': float(delta[protected].max())}
    for p in obj.data.polygons: p.use_smooth = True
    obj.data.update()
    if name.startswith('Head'):
        head_before, head_after = original.copy(), result.copy()
        obj.data.calc_loop_triangles()
        head_faces = np.array([tuple(f.vertices) for f in obj.data.loop_triangles], dtype=np.int32)

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART / 'avatar-v8.blend'))
(ART / 'validation/refinement-v8.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
