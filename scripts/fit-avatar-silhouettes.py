"""Compare and fit a local avatar mesh to the three approved reference views.

Runs with NumPy and Pillow. The tiny C++ rasterizer is compiled into /tmp;
no image or mesh is sent to an external service. Camera calibration is frozen
before shape fitting so both versions can be compared under identical views.
"""
from pathlib import Path
import ctypes, json, math, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artwork/avatar'
LIB = Path('/tmp/avatar_raster.dylib')
if not LIB.exists():
    subprocess.run(['clang++', '-O3', '-std=c++17', '-shared', '-fPIC', str(ROOT / 'scripts/avatar-raster.cpp'), '-o', str(LIB)], check=True)
lib = ctypes.CDLL(str(LIB))
ptr = np.ctypeslib.ndpointer
lib.raster.argtypes = [ctypes.c_int, ptr(np.float32, flags='C_CONTIGUOUS'), ctypes.c_int,
    ptr(np.int32, flags='C_CONTIGUOUS'), ptr(np.uint8, flags='C_CONTIGUOUS'),
    ctypes.c_int, ctypes.c_int, ptr(np.uint8, flags='C_CONTIGUOUS')]
data = np.load(ART / 'validation/v4/geometry.npz')
BASE = data['vertices'].astype(np.float64)
TRI = np.ascontiguousarray(data['triangles'], dtype=np.int32)
LABELS = np.ascontiguousarray(data['labels'], dtype=np.uint8)
PARTS = json.loads((ART / 'validation/v4/parts.json').read_text())
TARGETS = {n: np.load(ART / 'reference-inputs' / f'{n}-labels.npy') for n in ['three-quarter', 'side', 'rear']}
PALETTE = np.array([[255,255,255], [35,35,35], [246,169,120], [17,143,168]], np.uint8)

def basis(yaw, elevation):
    a, b = np.deg2rad([yaw, elevation])
    back = np.array([math.sin(a)*math.cos(b), -math.cos(a)*math.cos(b), math.sin(b)])
    right = np.array([math.cos(a), math.sin(a), 0])
    return right, np.cross(back, right), back

def raster(vertices, name, camera, ratio=.4, triangles=TRI, labels=LABELS):
    yaw, elev, scale, dx, dy = camera
    h, w = TARGETS[name].shape
    H, W = round(h*ratio), round(w*ratio)
    right, up, back = basis(yaw, elev)
    p = (vertices - [0,0,1.72]) @ np.stack([right,-up,back], axis=1)
    p[:,:2] *= 208 * scale * ratio
    p[:,0] += W/2 + dx*ratio
    p[:,1] += H/2 + dy*ratio
    p = np.ascontiguousarray(p, np.float32)
    out = np.zeros((H,W), np.uint8)
    lib.raster(len(p),p,len(triangles),triangles,labels,W,H,out)
    return out

def target(name, ratio):
    t = TARGETS[name]
    return np.array(Image.fromarray(t).resize((round(t.shape[1]*ratio),round(t.shape[0]*ratio)), Image.Resampling.NEAREST))

def overlap(a,b):
    return np.array([np.sum((a==i)&(b==i))/max(1,np.sum((a==i)|(b==i))) for i in range(1,4)])

def calibrate():
    cameras = {}
    ranges = {
        'three-quarter': ([17,6,1,-10,-12], [(17,17),(6,6),(.94,1.04),(-30,15),(-28,15)]),
        'side': ([80,6,1,8,-4], [(80,80),(6,6),(.94,1.04),(-20,30),(-28,15)]),
        'rear': ([206,6,1,0,-8], [(206,206),(6,6),(.94,1.04),(-25,25),(-28,15)])
    }
    for name,(initial,bounds) in ranges.items():
        t = target(name,.4)
        def score(p): return float(overlap(raster(BASE,name,p),t).mean())
        p=np.array(initial,float);best=score(p)
        for steps in [[3,2,.012,5,5],[1,1,.004,2,2],[.5,.5,.002,1,1]]:
            for cycle in range(6):
                improved=False
                for i,step in enumerate(steps):
                    for sign in [-1,1]:
                        q=p.copy();q[i]=np.clip(q[i]+step*sign,*bounds[i]);s=score(q)
                        if s>best+1e-6:p,best=q,s;improved=True
                if not improved:break
        cameras[name]=list(p)
        print(name, 'camera',list(p),'overlap',overlap(raster(BASE,name,p),t),flush=True)
    (ART/'validation/calibrated-cameras.json').write_text(json.dumps(cameras,indent=2))
    return cameras

def preview(vertices, label, cameras):
    out=ART/'validation'/label;out.mkdir(parents=True,exist_ok=True)
    report={}
    for name,camera in cameras.items():
        im=raster(vertices,name,camera,1)
        ref=TARGETS[name]
        report[name]=dict(zip(['hair','skin','cloth'],overlap(im,ref).tolist()))
        Image.fromarray(PALETTE[im]).save(out/f'{name}-silhouette.png')
        w,h=im.shape[1],im.shape[0]
        sheet=Image.new('RGB',(w*3,h+40),'white');draw=ImageDraw.Draw(sheet)
        for i,(title,arr) in enumerate([('Reference',PALETTE[ref]),(label,PALETTE[im]),('Overlay',((PALETTE[ref].astype(float)+PALETTE[im])/2).astype(np.uint8))]):
            draw.text((i*w+12,12),title,fill='black');sheet.paste(Image.fromarray(arr),(i*w,40))
        sheet.save(out/f'{name}-silhouette-comparison.png')
    (out/'silhouette-scores.json').write_text(json.dumps(report,indent=2))
    print(label,json.dumps(report),flush=True)

def deformation_basis():
    controls=[]
    def ids(prefix):
        out=np.zeros(len(BASE),bool)
        for name,(a,b) in PARTS.items():
            if name.startswith(prefix):out[a:b]=True
        return out
    hair=ids('Hair');skin=ids(('Head','Ear','Flat','Fine','Eye'));head=hair|skin
    cloth=~head;hood=ids('Hood —');body=cloth&~hood
    x,y,z=BASE.T
    def control(name,vec,bound=.16,regularize=.002):
        controls.append((name,np.ascontiguousarray(vec,np.float32),bound,regularize))
    def axis(name,axis,weight,bound=.16):
        v=np.zeros_like(BASE);v[:,axis]=weight;control(name,v,bound)
    # Broad changes act on all attached pieces and stay continuously curved.
    for height in [1.0,1.4,1.8,2.2,2.65]:
        g=np.exp(-.5*((z-height)/.29)**2)*skin
        axis(f'head width {height}',0,x*g,.12)
        front=1/(1+np.exp(np.clip(y/.10,-30,30)))
        axis(f'face profile {height}',1,g*front,.15)
        axis(f'back profile {height}',1,g*(1-front),.18)
    # A slight head tilt is visible in the reference eye line.
    v=np.zeros_like(BASE);v[:,0]=-(z-1.0)*head;v[:,2]=x*head
    control('head tilt',v,.075)
    for sign in [-1,1]:
        ear=ids('Ear L' if sign<0 else 'Ear R')
        for a in [0,1,2]:axis(f'ear {sign} position {a}',a,ear,.12)
        center=BASE[ear].mean(axis=0)
        control(f'ear {sign} size',(BASE-center)*ear[:,None],.16)
    # Fit the swept hair edge with angularly local controls, preserving the cap.
    theta=np.arctan2(x,-(y+.025))
    edge=np.exp(-np.maximum(z-2.30,0)**2/(2*.34**2))*hair
    for angle in [-140,-100,-75,-50,-25,0,22,45,70,95,125,155,180]:
        d=(theta-np.deg2rad(angle)+np.pi)%(2*np.pi)-np.pi
        g=np.exp(-.5*(d/np.deg2rad(18))**2)*edge
        axis(f'fringe elevation {angle}',2,g,.24)
        # Radial controls keep hair in contact with the fuller head.
        v=np.zeros_like(BASE);v[:,0]=np.sin(theta)*g;v[:,1]=-np.cos(theta)*g
        control(f'fringe radius {angle}',v,.13)
    axis('hair width',0,x*hair,.055)
    axis('hair depth',1,y*hair,.07)
    top=np.clip((z-2.8)/.35,0,1)*hair
    axis('hair crown height',2,top,.08)
    # The short cowlick should be a small flick, not an extra horn.
    short=(1/(1+np.exp(-(y-.40)/.035)))*np.clip((z-3.13)/.10,0,1)*hair
    control('short cowlick scale',(BASE-[.46,.39,3.115])*short[:,None],.48)
    for a in [0,1,2]:axis(f'cowlick position {a}',a,np.clip((z-3.19)/.14,0,1)*hair,.12)
    # Clothing silhouette: independent top/bottom width and front/back depth.
    for height in [0,.55,1.0]:
        g=np.exp(-.5*((z-height)/.30)**2)*cloth
        axis(f'clothes width {height}',0,x*g,.12)
        axis(f'clothes front {height}',1,g/(1+np.exp(np.clip(y/.09,-30,30))),.14)
        axis(f'clothes back {height}',1,g/(1+np.exp(np.clip(-y/.09,-30,30))),.14)
    for axis_id in [0,1,2]:axis(f'hood position {axis_id}',axis_id,hood,.13)
    for sign in [-1,1]:
        g=hood/(1+np.exp(np.clip(-sign*y/.12,-30,30)))
        axis(f'hood height {sign}',2,g,.14)
        axis(f'hood depth {sign}',1,g,.12)
    return controls

def fit(cameras):
    controls=deformation_basis()
    vertices=BASE.copy();parameters=np.zeros(len(controls))
    ratio=.4;targets={n:target(n,ratio) for n in cameras}
    weights={'three-quarter':.45,'side':.32,'rear':.23}
    def score(v,p):
        scores=[weights[n]*float(overlap(raster(v,n,cameras[n],ratio),targets[n]).mean()) for n in cameras]
        penalty=sum(reg*(a/bound)**2 for a,(_,_,bound,reg) in zip(p,controls))/len(controls)
        return sum(scores)-penalty
    start=score(vertices,parameters);best=start
    for step in [.07,.035,.0175,.00875]:
        for cycle in range(8):
            improved=0
            for i,(name,delta,bound,reg) in enumerate(controls):
                for sign in [-1,1]:
                    change=np.clip(parameters[i]+step*sign,-bound,bound)-parameters[i]
                    if abs(change)<1e-7:continue
                    candidate=vertices+delta*change;p=parameters.copy();p[i]+=change
                    value=score(candidate,p)
                    if value>best+1e-5:
                        parameters,vertices,best=p,candidate,value;improved+=1
            print('fit',step,cycle,'overlap',round(best,5),'improvements',improved,flush=True)
            if not improved:break
    out=ART/'validation/v5-fit';out.mkdir(parents=True,exist_ok=True)
    np.save(out/'fitted-vertices.npy',vertices.astype(np.float32))
    report={'before':start,'after':best,'parameters':{c[0]:float(p) for c,p in zip(controls,parameters)}}
    (out/'fit-parameters.json').write_text(json.dumps(report,indent=2))
    preview(vertices,'v5-fit',cameras)

if __name__=='__main__':
    if '--calibrate' in sys.argv:
        cameras=calibrate();preview(BASE,'v4-calibrated',cameras)
    else:
        cameras=json.loads((ART/'validation/calibrated-cameras.json').read_text())
        if '--fit' in sys.argv:fit(cameras)
        else:preview(BASE,'v4-calibrated',cameras)
