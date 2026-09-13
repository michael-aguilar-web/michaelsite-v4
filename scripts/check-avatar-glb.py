"""Validate the browser asset without opening a browser or uploading it."""
from pathlib import Path
import struct, json, math, sys

root=Path(__file__).resolve().parents[1]
raw=(root/'public/models/avatar.glb').read_bytes()
magic,version,length=struct.unpack_from('<III',raw)
assert magic==0x46546c67 and version==2 and length==len(raw)
json_len,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
model=json.loads(raw[20:20+json_len]);bin_offset=20+json_len
bin_len,kind=struct.unpack_from('<II',raw,bin_offset);assert kind==0x004e4942
binary=raw[bin_offset+8:bin_offset+8+bin_len]
assert not model.get('cameras')
assert all('uri' not in im for im in model.get('images',[]))
assert all('Reference' not in n.get('name','') and 'Trace' not in n.get('name','') for n in model['nodes'])
for view in model['bufferViews']:assert view.get('byteOffset',0)+view['byteLength']<=len(binary)
vertices=triangles=0
for mesh in model['meshes']:
    for primitive in mesh['primitives']:
        acc=model['accessors'][primitive['attributes']['POSITION']]
        view=model['bufferViews'][acc['bufferView']]
        assert acc['componentType']==5126 and acc['type']=='VEC3'
        start=view.get('byteOffset',0)+acc.get('byteOffset',0);stride=view.get('byteStride',12)
        for i in range(acc['count']):assert all(math.isfinite(v) for v in struct.unpack_from('<fff',binary,start+i*stride))
        vertices+=acc['count']
        ids=model['accessors'][primitive['indices']];view=model['bufferViews'][ids['bufferView']]
        begin=view.get('byteOffset',0)+ids.get('byteOffset',0)
        fmt={5121:'B',5123:'H',5125:'I'}[ids['componentType']]
        values=struct.unpack_from('<'+str(ids['count'])+fmt,binary,begin)
        assert max(values)<acc['count'];triangles+=ids['count']//3
report={'bytes':len(raw),'exportedVertices':vertices,'triangles':triangles,'embeddedImages':len(model.get('images',[])),'externalResources':0,'geometry':'valid'}
revision=sys.argv[1] if len(sys.argv)>1 else 'v5'
(root/f'artwork/avatar/validation/glb-{revision}-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
