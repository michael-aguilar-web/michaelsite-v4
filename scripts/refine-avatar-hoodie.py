"""Soften the hood and seat its cords, preserving the accepted v9 head.

Always reads the v9 save point and writes a separate v10 scene. Only the hood,
two cords, and their rounded ends may change; all other model parts are locked.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artwork/avatar'
bpy.ops.wm.open_mainfile(filepath=str(ART/'avatar-v9.blend'))
scene = bpy.context.scene
HOOD = 'Hood — traced neckline and back'
editable = {HOOD, 'Hood drawstring', 'Hood drawstring.001',
            'Drawstring rounded end', 'Drawstring rounded end.001'}


def signature(obj):
    """Include topology, transforms, UVs, and material assignments in the lock."""
    digest = hashlib.sha256()
    digest.update(np.array(obj.matrix_world, dtype=np.float64).tobytes())
    digest.update(np.array([v.co[:] for v in obj.data.vertices], np.float32).tobytes())
    for p in obj.data.polygons:
        digest.update(np.array([*p.vertices, p.material_index, p.use_smooth], np.int32).tobytes())
    for uv in obj.data.uv_layers:
        digest.update(np.array([p.uv[:] for p in uv.data], np.float32).tobytes())
    digest.update('|'.join(m.name for m in obj.data.materials).encode())
    return digest.hexdigest()


locked = {o.name: signature(o) for o in scene.objects
          if o.type == 'MESH' and o.get('avatar_part') and o.name not in editable}


def ease(a, b, value):
    t = max(0., min(1., (value-a)/(b-a)))
    return t*t*(3.-2.*t)


# A thinner rolled front opens into a longer hanging back panel. The bottom
# sinks between the shoulder supports; its upper edge is gently uneven instead
# of a level torus. Broad folds remain appropriate to the simple reference art.
hood = bpy.data.objects[HOOD]
vertices, faces = [], []
n, sides = 192, 64
for i in range(n):
    a = 2*math.pi*i/n
    sn, cs = math.sin(a), math.cos(a)
    front, rear = max(cs, 0.), max(-cs, 0.)
    vee = front*(1-(math.sqrt(sn*sn+.0016)-.04)**.92)
    center = 1.030+.060*front-.305*vee
    center -= .010*rear**2
    center += .008*sn*math.sin(2*a)
    for j in range(sides):
        b = 2*math.pi*j/sides
        c, s = math.cos(b), math.sin(b)
        lower = max(-s, 0.)
        upper = max(s, 0.)
        radial = .230-.012*front
        x = (.575+radial*c)*sn+.095*(1-front**4)
        y = .04-(.51-.16*front+(.195+.05*front)*c)*cs
        z = center+(.153+.052*rear-.054*front)*upper
        z -= (.173-.074*front)*lower
        z -= .315*rear**1.10*lower**1.25
        # Roll the outer back panel down from the neckline. This places its
        # fullest curve below the rim instead of creating a vertical rear wall.
        z -= .115*rear*max(c,0.)
        # Let the hanging fabric fall back and taper gently toward the tip.
        x -= .020*sn*rear*lower**2
        y += .020*rear**1.5*lower**1.3
        # Soft shoulder compression and two very shallow rear folds.
        z -= .014*math.exp(-((abs(sn)-.87)/.14)**2)*upper
        z -= .035*abs(sn)**6*max(c,0.)
        rear_face = rear**2*max(c, 0.)**.7
        y += rear_face*(.010*math.cos(3*a+.25)-.008*math.cos(7*a-.2))
        # A faint curved seam on the rear, modeled into the cloth itself.
        seam = .06+.045*(1-s)
        y -= .010*rear_face*math.exp(-((x-seam)/.022)**2)
        vertices.append((x*1.08, y, z))
for i in range(n):
    for j in range(sides):
        faces.append((i*sides+j, ((i+1)%n)*sides+j,
                      ((i+1)%n)*sides+(j+1)%sides, i*sides+(j+1)%sides))
mesh = bpy.data.meshes.new('Soft collar and hanging hood')
mesh.from_pydata(vertices, [], faces)
mesh.update()
hood.data = mesh
hood.matrix_world = Matrix.Identity(4)
mesh.materials.append(bpy.data.materials['Teal hoodie'])
mesh.materials.append(bpy.data.materials['Hood lining'])
bm = bmesh.new(); bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges), 'Hood must be a closed cloth volume'
bm.to_mesh(mesh); bm.free()
for f in mesh.polygons:
    f.use_smooth = True
    f.material_index = int(math.cos(2*math.pi*(f.index%sides+.5)/sides) < -.62)

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
body_tree = BVHTree.FromObject(bpy.data.objects['Hoodie body'], depsgraph)
hood_tree = BVHTree.FromObject(hood, depsgraph)


def front_hit(tree, x, z):
    return tree.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))[0]


def surface(x, z):
    hits = [h for h in (front_hit(body_tree, x, z), front_hit(hood_tree, x, z)) if h is not None]
    if not hits:
        raise RuntimeError(f'Cord outside hoodie: {x}, {z}')
    return min(h.y for h in hits)


for name in editable-{HOOD}:
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

report = {'source': 'v9', 'lockedParts': locked, 'cords': []}
for side, anchor_x, anchor_z, end_z in [(-1, -.255, .886, .034), (1, .205, .875, .030)]:
    radius = .030
    root = front_hit(hood_tree, anchor_x, anchor_z)
    assert root is not None, 'Drawstring must originate in the hood'
    centers = []
    count = 112
    for i in range(count):
        t = i/(count-1)
        z = anchor_z+(end_z-anchor_z)*t
        # Small natural bow, with the cord lying against the chest below it.
        x = anchor_x+side*(.030*math.sin(math.pi*t*.75)+.006*t)
        contact = surface(x, z)
        # The first cap is buried inside the collar. It exits over a short
        # descending arc, so no pale detached end is visible above the string.
        clearance = -.045+.073*ease(0., .125, t)
        centers.append(Vector((x, contact-clearance, z)))
    # Smooth the varying collar/chest clearance, then prevent the exposed cord
    # from penetrating the chest. Keep the embedded root fixed.
    yy = np.array([p.y for p in centers])
    for _ in range(90):
        yy[1:-1] = .25*yy[:-2]+.5*yy[1:-1]+.25*yy[2:]
    for i, p in enumerate(centers):
        p.y = yy[i]
        body_hit = front_hit(body_tree, p.x, p.z)
        if body_hit is not None:
            limit = body_hit.y-radius*.92
            # A smooth minimum avoids a kink where the hanging cord begins
            # resting on the chest. Blend out the root's buried section.
            clamped = .5*(p.y+limit-math.sqrt((p.y-limit)**2+.008**2))
            weight = ease(.06,.20,i/(count-1))
            p.y = p.y*(1-weight)+clamped*weight

    cord_vertices, cord_faces = [], []
    radial_steps = 16
    for i, p in enumerate(centers):
        tangent = centers[min(i+1,count-1)]-centers[max(i-1,0)]
        tangent.normalize()
        across = tangent.cross(Vector((0,1,0))).normalized()
        around = tangent.cross(across).normalized()
        for j in range(radial_steps):
            b = 2*math.pi*j/radial_steps
            cord_vertices.append(tuple(p+radius*(across*math.cos(b)+around*math.sin(b))))
    for i in range(count-1):
        for j in range(radial_steps):
            cord_faces.append((i*radial_steps+j,i*radial_steps+(j+1)%radial_steps,
                               (i+1)*radial_steps+(j+1)%radial_steps,(i+1)*radial_steps+j))
    cord_faces.extend([tuple(reversed(range(radial_steps))),
                       tuple((count-1)*radial_steps+j for j in range(radial_steps))])
    cord_mesh = bpy.data.meshes.new('Collar-attached cord')
    cord_mesh.from_pydata(cord_vertices, [], cord_faces); cord_mesh.update()
    bm=bmesh.new();bm.from_mesh(cord_mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges)
    bm.to_mesh(cord_mesh);bm.free()
    cord = bpy.data.objects.new('Hood drawstring', cord_mesh)
    scene.collection.objects.link(cord)
    cord['avatar_part'] = True
    cord_mesh.materials.append(bpy.data.materials['Warm white drawstrings'])
    for f in cord_mesh.polygons: f.use_smooth = True
    # The rounded end now belongs at the hanging tip, not at the collar root.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=centers[-1])
    end=bpy.context.object;end.name='Drawstring rounded end';end['avatar_part']=True
    end.data.materials.append(bpy.data.materials['Warm white drawstrings'])
    for f in end.data.polygons:f.use_smooth=True
    near, normal, _, _ = hood_tree.find_nearest(centers[0])
    signed_distance = (centers[0]-near).dot(normal)
    assert signed_distance < -radius, 'The entire drawstring root must be buried in the hood'
    report['cords'].append({'side':side,'root':list(centers[0]),
                            'rootSignedDistance':signed_distance,'radius':radius})

for name, original in locked.items():
    assert signature(bpy.data.objects[name]) == original, f'Locked part changed: {name}'
report['lockedPartsUnchanged'] = True
report['hoodVertices'] = len(mesh.vertices)
(ART/'validation/refinement-v10.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'avatar-v10.blend'))
print(json.dumps(report,indent=2), flush=True)
