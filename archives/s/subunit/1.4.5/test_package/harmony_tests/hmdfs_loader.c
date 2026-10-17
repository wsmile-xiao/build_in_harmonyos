/* Native signed library on HMDFS: real UTF-8 protocol emission and readback. */
#define _POSIX_C_SOURCE 200809L
#if !defined(__OHOS__) || !defined(__aarch64__)
#error Native HarmonyOS PC aarch64 required
#endif
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>
#ifdef SUBUNIT_DIRECT
#include <subunit/child.h>
#endif

int main(int argc, char **argv) {
    struct utsname platform;
    struct stat parent, info;
    char path[4096], library[4096], bytes[256];
    const char expected[] = "test: 鸿蒙消费者\nsuccess: 鸿蒙消费者\n";
    void *handle = NULL;
    void (*begin)(const char *) = NULL, (*pass)(const char *) = NULL;
    int fd = -1, saved = -1, rc = 1, exists = 0;
    ssize_t n;
    if (argc != 3 || uname(&platform) || strcmp(platform.sysname,"HarmonyOS") ||
        strcmp(platform.machine,"aarch64") || strncmp(argv[1],"/storage/Users/",15) ||
        strncmp(argv[2],"/storage/Users/",15) || stat(argv[2],&parent) || !S_ISDIR(parent.st_mode)) goto cleanup;
    if (snprintf(path,sizeof(path),"%s/鸿蒙协议-%ld.txt",argv[2],(long)getpid()) >= (int)sizeof(path) ||
        snprintf(library,sizeof(library),"%s/libsubunit.so.1.4.5",argv[1]) >= (int)sizeof(library)) goto cleanup;
#ifdef SUBUNIT_DIRECT
    begin = subunit_test_start;
    pass = subunit_test_pass;
#else
    handle = dlopen(library,RTLD_NOW|RTLD_LOCAL);
    if (!handle) { fprintf(stderr,"dlopen: %s\n",dlerror()); goto cleanup; }
    begin = (void (*)(const char *))dlsym(handle,"subunit_test_start");
    pass = (void (*)(const char *))dlsym(handle,"subunit_test_pass");
#endif
    if (!begin || !pass || fflush(stdout)) goto cleanup;
    fd = open(path,O_CREAT|O_EXCL|O_RDWR,0600);
    if (fd < 0) goto cleanup;
    exists = 1;
    saved = dup(STDOUT_FILENO);
    if (saved < 0 || dup2(fd,STDOUT_FILENO) < 0) goto cleanup;
    begin("鸿蒙消费者"); pass("鸿蒙消费者");
    if (fflush(stdout) || dup2(saved,STDOUT_FILENO) < 0) goto cleanup;
    if (close(saved)) { saved=-1; goto cleanup; }
    saved=-1;
    if (fstat(fd,&info) || info.st_uid != parent.st_uid || info.st_size != sizeof(expected)-1) goto cleanup;
    if (close(fd)) { fd=-1; goto cleanup; }
    fd=-1;
    fd=open(path,O_RDONLY);
    if (fd < 0) goto cleanup;
    n=read(fd,bytes,sizeof(bytes));
    if (n != (ssize_t)(sizeof(expected)-1) || memcmp(bytes,expected,sizeof(expected)-1)) goto cleanup;
    printf("file_uid=%lu parent_uid=%lu process_uid=%lu bytes=%ld\n",
           (unsigned long)info.st_uid,(unsigned long)parent.st_uid,(unsigned long)getuid(),(long)n);
    rc=0;
cleanup:
    if (saved >= 0) {
        if (dup2(saved,STDOUT_FILENO) < 0) rc=1;
        if (close(saved)) rc=1;
    }
    if (fd >= 0 && close(fd)) rc=1;
    if (handle && dlclose(handle)) rc=1;
    if (exists && (unlink(path) || access(path,F_OK) == 0)) rc=1;
    if (!rc) puts("HARMONY_TEST_PASS=1/1");
    else fputs("FAIL: native HMDFS signed subunit protocol\n",stderr);
    return rc;
}
