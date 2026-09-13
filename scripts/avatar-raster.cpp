#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>
extern "C" void raster(int nv,const float* p,int nt,const int32_t* f,const uint8_t* labels,int w,int h,uint8_t* out){
 std::vector<float> depth(w*h,-1e20f);std::fill(out,out+w*h,0);
 for(int t=0;t<nt;t++){
  int ia=f[3*t],ib=f[3*t+1],ic=f[3*t+2];const float *a=p+3*ia,*b=p+3*ib,*c=p+3*ic;
  float den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);if(std::abs(den)<1e-10f)continue;
  int x0=std::max(0,int(std::floor(std::min({a[0],b[0],c[0]})))),x1=std::min(w-1,int(std::ceil(std::max({a[0],b[0],c[0]}))));
  int y0=std::max(0,int(std::floor(std::min({a[1],b[1],c[1]})))),y1=std::min(h-1,int(std::ceil(std::max({a[1],b[1],c[1]}))));
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
   float u=((b[1]-c[1])*(x+.5f-c[0])+(c[0]-b[0])*(y+.5f-c[1]))/den;
   float v=((c[1]-a[1])*(x+.5f-c[0])+(a[0]-c[0])*(y+.5f-c[1]))/den;
   if(u<0||v<0||u+v>1)continue;float z=u*a[2]+v*b[2]+(1-u-v)*c[2];int i=y*w+x;
   if(z>depth[i]){depth[i]=z;out[i]=labels[t];}
  }
 }
}
