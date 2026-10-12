#include "../http_fixture.h"
#include <onion/handlers/exportlocal.h>
#include <onion/handler.h>
#include <sys/utsname.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
int main(int argc,char **argv) {
    struct utsname identity;
    if(argc!=2 || uname(&identity) || strcmp(identity.sysname,"HarmonyOS") || strcmp(identity.machine,"aarch64")) return 1;
    const char *name="鸿蒙-onion-文件.txt";
    const char *bytes="HarmonyOS HMDFS UTF-8 onion export-local roundtrip\n";
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/%s",argv[1],name)>=(int)sizeof(path)) return 1;
    struct stat parent;
    if(lstat(argv[1],&parent) || !S_ISDIR(parent.st_mode) || S_ISLNK(parent.st_mode)) return 1;
    int fd=open(path,O_CREAT|O_EXCL|O_WRONLY,0600); if(fd<0) return 1;
    size_t count=strlen(bytes),at=0;
    while(at<count) {
        ssize_t n=write(fd,bytes+at,count-at);
        if(n<0 && errno==EINTR) continue;
        if(n<=0) { close(fd); unlink(path); return 1; } at+=(size_t)n;
    }
    int rc=fsync(fd); if(close(fd)) rc=1;
    struct stat created;
    if(rc || lstat(path,&created) || created.st_size!=(off_t)count || !S_ISREG(created.st_mode) || created.st_uid!=parent.st_uid) { unlink(path); return 1; }
    fixture f; alarm(20);
    if(fixture_init(&f)) { unlink(path); return 1; }
    onion_handler *handler=onion_handler_export_local_new(argv[1]);
    if(!handler) rc=1;
    else {
        onion_set_root_handler(f.server,handler);
        if(fixture_start(&f)) rc=1;
        else {
            char response[8192];
            const char *url="/%E9%B8%BF%E8%92%99-onion-%E6%96%87%E4%BB%B6.txt";
            if(fixture_get(&f,url,response,sizeof(response))) rc=1;
            else {
                char *body=strstr(response,"\r\n\r\n");
                if(!strstr(response,"HTTP/1.1 200") || !body || strlen(body+4)!=count || memcmp(body+4,bytes,count)) rc=1;
            }
        }
    }
    if(fixture_end(&f)) rc=1;
    if(unlink(path) || !lstat(path,&created) || errno!=ENOENT) rc=1;
    if(!rc) printf("HARMONY_TEST_PASS=1/1; OS=HarmonyOS/aarch64; bytes=%zu; uid=%lu; projected_uid=%lu; HTTP_UTF8_EXACT; CLEANUP_PASS\n",count,(unsigned long)getuid(),(unsigned long)parent.st_uid);
    else fputs("FAIL: HarmonyOS HMDFS UTF-8 file via real onion HTTP\n",stderr);
    return rc;
}
