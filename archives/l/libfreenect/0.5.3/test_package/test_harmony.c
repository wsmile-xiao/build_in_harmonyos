#include <dlfcn.h>
#include <stdio.h>
#include <sys/utsname.h>

/* HarmonyOS-specific test:
 * On HarmonyOS, an ELF shared library that is not properly code-signed
 * (binary-sign-tool) cannot be dlopen()'d. This test loads the packaged
 * libfreenect.so and libfreenect_sync.so at runtime, which directly
 * validates the OHOS ELF signing step in the recipe. It also prints the
 * target uname to prove the binary actually ran on the HarmonyOS aarch64
 * device rather than on the build host. */
int main(void)
{
    struct utsname u;
    if (uname(&u) == 0) {
        printf("target: %s %s %s\n", u.sysname, u.release, u.machine);
    }

    void *h = dlopen("libfreenect.so", RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen libfreenect.so failed: %s\n", dlerror());
        return 1;
    }

    void *h2 = dlopen("libfreenect_sync.so", RTLD_NOW | RTLD_GLOBAL);
    if (!h2) {
        fprintf(stderr, "dlopen libfreenect_sync.so failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    printf("test harmony: OK (signed .so loadable on HarmonyOS)\n");
    dlclose(h);
    dlclose(h2);
    return 0;
}
