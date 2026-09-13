"""Check whether hood/shirt intersections are exposed around the turntable."""
from pathlib import Path
import bpy,json,math,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artwork/avatar'
versions=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['v11']

def geometry(objects):
    vertices=[];faces=[]
    for obj in objects:
        obj.data.calc_loop_triangles();start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in f.vertices) for f in obj.data.loop_triangles)
    return vertices,faces,BVHTree.FromPolygons(vertices,faces,all_triangles=True)

def crossings(a,b):
    hits=[]
    for tri,other in ((a,b),(b,a)):
        for i in range(3):
            origin=tri[i];delta=tri[(i+1)%3]-origin;length=delta.length
            if length<1e-9:continue
            direction=delta/length
            hit=intersect_ray_tri(*other,direction,origin,True)
            if hit is not None and -.00001<=(hit-origin).dot(direction)<=length+.00001:
                hits.append(hit)
    return sum(hits,Vector())/len(hits) if hits else None

for version in versions:
    bpy.ops.wm.open_mainfile(filepath=str(ART/f'avatar-{version}.blend'))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('avatar_part')]
    av,af,hood=geometry([o for o in objects if o.name.startswith('Hood —')])
    bv,bf,body=geometry([o for o in objects if o.name.startswith(('Hoodie body','Soft raglan sleeve'))])
    _,_,whole=geometry(objects)
    pairs=hood.overlap(body);points=[]
    for i,j in pairs:
        p=crossings([av[k] for k in af[i]],[bv[k] for k in bf[j]])
        if p is not None:points.append(p)
    views={};rear_views={}
    for angle in range(0,360,15):
        yaw=math.radians(angle);elev=math.radians(6)
        direction=Vector((math.sin(yaw)*math.cos(elev),-math.cos(yaw)*math.cos(elev),math.sin(elev)))
        count=0;rear_count=0
        for p in points:
            hit,_,_,_=whole.ray_cast(p+direction*5,-direction)
            if hit is not None and (hit-p).length<.0015:
                count+=1
                if p.y>0:rear_count+=1
        views[str(angle)]=count
        rear_views[str(angle)]=rear_count
    report={'version':version,'intersectingTrianglePairs':len(pairs),'crossingSamples':len(points),
            'visibleCrossingsByAngle':views,'rearGarmentVisibleCrossingsByAngle':rear_views,
            'maximumVisibleCrossings':max(views.values()),
            'note':'Intersection samples locate joins; counts depend on tessellation and are not visual error scores.'}
    (ART/f'validation/clothing-contact-{version}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
