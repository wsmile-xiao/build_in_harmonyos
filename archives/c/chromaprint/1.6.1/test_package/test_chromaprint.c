#include <chromaprint.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/utsname.h>

static int assertions;
#define CHECK(x) do { assertions++; if (!(x)) { fprintf(stderr, "FAIL line=%d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(void) {
    const int rate=11025, size=rate*12;
    int16_t *samples=malloc((size_t)size*sizeof(*samples));
    CHECK(samples != NULL);
    for(int i=0;i<size;i++) samples[i]=(int16_t)(10000*sin(6.283185307179586*440*i/rate)+5000*sin(6.283185307179586*660*i/rate));
    CHECK(strcmp(chromaprint_get_version(), "1.6.1")==0);
    ChromaprintContext *ctx=chromaprint_new(CHROMAPRINT_ALGORITHM_DEFAULT);
    CHECK(ctx != NULL);
    CHECK(chromaprint_start(ctx,rate,1)==1);
    CHECK(chromaprint_feed(ctx,samples,size)==1);
    CHECK(chromaprint_finish(ctx)==1);
    uint32_t *raw=NULL, *decoded=NULL;
    int count=0, decoded_count=0, algorithm=-1, encoded_size=0;
    char *encoded=NULL;
    CHECK(chromaprint_get_raw_fingerprint(ctx,&raw,&count)==1);
    CHECK(count>0 && raw!=NULL);
    CHECK(chromaprint_encode_fingerprint(raw,count,CHROMAPRINT_ALGORITHM_DEFAULT,&encoded,&encoded_size,1)==1);
    CHECK(encoded_size>0 && encoded!=NULL);
    CHECK(chromaprint_decode_fingerprint(encoded,encoded_size,&decoded,&decoded_count,&algorithm,1)==1);
    CHECK(decoded_count==count && algorithm==CHROMAPRINT_ALGORITHM_DEFAULT);
    CHECK(memcmp(raw,decoded,(size_t)count*sizeof(*raw))==0);
    uint32_t hash1=0,hash2=0;
    CHECK(chromaprint_get_fingerprint_hash(ctx,&hash1)==1);
    CHECK(chromaprint_hash_fingerprint(decoded,decoded_count,&hash2)==1);
    CHECK(hash1==hash2);
#ifdef __OHOS__
    struct utsname system;
    CHECK(uname(&system)==0 && strcmp(system.sysname,"HarmonyOS")==0);
    const char *tmp=getenv("TMPDIR");
    CHECK(tmp!=NULL && tmp[0]=='/');
    char path[4096];
    CHECK(snprintf(path,sizeof(path),"%s/chromaprint-XXXXXX",tmp)<(int)sizeof(path));
    int fd=mkstemp(path);
    CHECK(fd>=0);
    CHECK(write(fd,encoded,(size_t)encoded_size)==encoded_size);
    char *readback=calloc((size_t)encoded_size,1);
    CHECK(readback!=NULL);
    CHECK(pread(fd,readback,(size_t)encoded_size,0)==encoded_size);
    CHECK(memcmp(readback,encoded,(size_t)encoded_size)==0);
    CHECK(close(fd)==0);
    CHECK(unlink(path)==0);
    free(readback);
#endif
    chromaprint_dealloc(decoded); chromaprint_dealloc(encoded); chromaprint_dealloc(raw);
    chromaprint_free(ctx); free(samples);
    printf("CONSUMER_1_OF_1_PASS assertions=%d fingerprint_items=%d\n",assertions,count);
    return 0;
}
