#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <webp/decode.h>
#include <webp/encode.h>
#include <webp/mux.h>
#include <webp/demux.h>

#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %s:%d %s\n",__FILE__,__LINE__,#c); return 1; } } while (0)
int main(void) {
  unsigned char rgba[4*8*8], *encoded=NULL, *decoded=NULL;
  int x,y,w=0,h=0;
  for(y=0;y<8;++y) for(x=0;x<8;++x) {
    int i=4*(y*8+x); rgba[i]=(unsigned char)(x*31);
    rgba[i+1]=(unsigned char)(y*29); rgba[i+2]=127; rgba[i+3]=255;
  }
  CHECK(WebPGetDecoderVersion()>=0x010600);
  CHECK(WebPGetEncoderVersion()>=0x010600);
  size_t n=WebPEncodeLosslessRGBA(rgba,8,8,32,&encoded); CHECK(n>0 && encoded);
  CHECK(WebPGetInfo(encoded,n,&w,&h) && w==8 && h==8);
  decoded=WebPDecodeRGBA(encoded,n,&w,&h); CHECK(decoded && w==8 && h==8);
  CHECK(memcmp(decoded,rgba,sizeof rgba)==0); WebPFree(decoded);
  puts("CONSUMER lossless_rgba_roundtrip PASS");
  WebPData data={encoded,n}, assembled={NULL,0};
  WebPMux *mux=WebPMuxCreate(&data,1); CHECK(mux);
  const unsigned char text[]="libwebp actual consumer metadata";
  WebPData meta={text,sizeof text};
  CHECK(WebPMuxSetChunk(mux,"XMP ",&meta,1)==WEBP_MUX_OK);
  CHECK(WebPMuxAssemble(mux,&assembled)==WEBP_MUX_OK); CHECK(assembled.size>n);
  WebPDemuxer *demux=WebPDemux(&assembled); CHECK(demux);
  CHECK(WebPDemuxGetI(demux,WEBP_FF_CANVAS_WIDTH)==8);
  CHECK(WebPDemuxGetI(demux,WEBP_FF_CANVAS_HEIGHT)==8);
  WebPChunkIterator chunk; CHECK(WebPDemuxGetChunk(demux,"XMP ",1,&chunk));
  CHECK(chunk.chunk.size==sizeof text && memcmp(chunk.chunk.bytes,text,sizeof text)==0);
  WebPDemuxReleaseChunkIterator(&chunk); WebPDemuxDelete(demux); WebPMuxDelete(mux);
  WebPDataClear(&assembled); WebPFree(encoded);
  puts("CONSUMER mux_demux_metadata_roundtrip PASS");
  n=WebPEncodeRGBA(rgba,8,8,32,90.0f,&encoded); CHECK(n>0 && encoded);
  decoded=WebPDecodeRGBA(encoded,n,&w,&h); CHECK(decoded && w==8 && h==8);
  for(x=0;x<8*8;++x) CHECK(decoded[4*x+3]==255);
  WebPFree(decoded); WebPFree(encoded);
  puts("CONSUMER lossy_rgba_dimensions_alpha PASS");
  CHECK(WebPDecodeRGBA((const unsigned char*)"bad",3,&w,&h)==NULL);
  puts("CONSUMER malformed_bitstream_rejection PASS");
  puts("CONSUMER_COUNT=4\nCONSUMER 4/4 PASS"); return 0;
}
