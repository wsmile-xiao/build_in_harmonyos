/*
 * libopencsd HarmonyOS-specific dynamic-loading test.
 *
 * Loads the packaged libraries with dlopen() (no link-time dependency):
 *  1. pre-loads the core shared object libopencsd.so.1 by absolute path
 *     (registers it with the platform dynamic loader);
 *  2. loads libopencsd_c_api.so — its dependency on libopencsd.so.1 resolves
 *     against the already-loaded image (this is the resolution step that
 *     differs between HarmonyOS/bionic and host loaders);
 *  3. resolves the C API symbol ocsd_get_version via dlsym and verifies the
 *     returned version number.
 *
 * This exercises the platform dynamic loader against the artifacts produced
 * by the OHOS toolchain (lld-built .so), i.e. the true HarmonyOS integration
 * point of the packaged library.
 *
 * Usage: ocsd_dlopen <path-to-libopencsd.so.1> <path-to-libopencsd_c_api.so>
 */
#include <stdint.h>
#include <stdio.h>

#include <dlfcn.h>

typedef uint32_t (*fn_get_version)(void);

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <libopencsd.so.1> <libopencsd_c_api.so>\n",
                argv[0]);
        return 2;
    }

    /* 1) pre-load the core library so the c_api dependency can resolve */
    void *core = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!core) {
        fprintf(stderr, "FAIL: dlopen('%s') failed: %s\n", argv[1], dlerror());
        return 3;
    }

    /* 2) load the C-API library; its DT_NEEDED libopencsd.so.1 must resolve
       against the image loaded above */
    void *handle = dlopen(argv[2], RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen('%s') failed: %s\n", argv[2], dlerror());
        return 4;
    }

    fn_get_version fn = (fn_get_version)dlsym(handle, "ocsd_get_version");
    if (!fn) {
        fprintf(stderr, "FAIL: dlsym(ocsd_get_version) failed: %s\n", dlerror());
        return 5;
    }

    uint32_t vnum = fn();
    if (vnum != 0x010505) {
        fprintf(stderr, "FAIL: version via dlopen got 0x%06x, want 0x010505\n",
                vnum);
        return 6;
    }

    printf("PASS: dlopen chain OK, ocsd_get_version = 0x%06x\n", vnum);
    return 0;
}
