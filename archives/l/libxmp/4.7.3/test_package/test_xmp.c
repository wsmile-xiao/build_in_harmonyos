#include <xmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>
#define CHECK(x) do { ++assertions; if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); goto fail; } } while(0)
int main(void) {
    int assertions=0, loaded=0, started=0, result=1;
    xmp_context context=xmp_create_context();
    unsigned char module[1084+1024+64]={0};
    char filename[1024]={0};
    FILE *output=NULL;
    CHECK(context != NULL);
    memcpy(module,"HarmonyOS PCM",13);
    module[43]=32; module[45]=64; module[49]=32;
    module[950]=1; memcpy(module+1080,"M.K.",4);
    module[1084]=1; module[1085]=0xac; module[1086]=0x10;
    for(int i=0;i<64;i++) module[1084+1024+i]=(unsigned char)(i<32 ? 4*i : 252-4*i);
    CHECK(xmp_load_module_from_memory(context,module,sizeof(module)) == 0); loaded=1;
    struct xmp_module_info info;
    xmp_get_module_info(context,&info);
    CHECK(info.mod && info.mod->chn == 4 && info.mod->len == 1);
    CHECK(xmp_start_player(context,44100,0) == 0); started=1;
    const char *tmp=getenv("TMPDIR"); CHECK(tmp && *tmp);
    CHECK(snprintf(filename,sizeof(filename),"%s/xmp-PCM-XXXXXX",tmp) < (int)sizeof(filename));
    int fd=mkstemp(filename); CHECK(fd >= 0);
    output=fdopen(fd,"wb"); if(!output) close(fd); CHECK(output != NULL);
    size_t bytes=0; int nonzero=0;
    for(int frame=0;frame<40;frame++) {
        CHECK(xmp_play_frame(context) == 0);
        struct xmp_frame_info played; xmp_get_frame_info(context,&played);
        CHECK(played.buffer && played.buffer_size > 0);
        for(int i=0;i<played.buffer_size;i++) nonzero |= ((unsigned char*)played.buffer)[i];
        CHECK(fwrite(played.buffer,1,(size_t)played.buffer_size,output) == (size_t)played.buffer_size);
        bytes += (size_t)played.buffer_size;
    }
    CHECK(bytes > 0 && nonzero);
    CHECK(fflush(output) == 0 && fseek(output,0,SEEK_END) == 0 && (size_t)ftell(output) == bytes);
#ifdef __OHOS__
    struct utsname platform;
    CHECK(uname(&platform) == 0 && strstr(platform.sysname,"HarmonyOS"));
#endif
    printf("CONSUMER_1_OF_1_PASS assertions=%d pcm_bytes=%zu\n",assertions,bytes);
    result=0;
fail:
    if(output) fclose(output);
    if(*filename) unlink(filename);
    if(context){if(started) xmp_end_player(context); if(loaded) xmp_release_module(context); xmp_free_context(context);}
    return result;
}
