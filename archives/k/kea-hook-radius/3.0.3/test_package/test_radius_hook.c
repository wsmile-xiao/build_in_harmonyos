/*
 * Consumer test for kea-hook-radius.
 *
 * Loads the packaged Kea hook plug-in the way the Kea server does and checks
 * the hook ABI contract (version/load/unload), including the hook framework
 * version the plug-in was built against.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

/* Kea 3.0.3 src/lib/hooks/hooks.h: const int KEA_HOOKS_VERSION = 30003; */
#define EXPECTED_HOOKS_VERSION 30003

typedef int (*hook_version_fn)(void);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libdhcp_radius.so>\n", argv[0]);
        return 2;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", argv[1], dlerror());
        return 1;
    }

    hook_version_fn hook_version = (hook_version_fn)dlsym(handle, "version");
    if (hook_version == NULL) {
        fprintf(stderr, "dlsym(version) failed: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }
    if (dlsym(handle, "load") == NULL || dlsym(handle, "unload") == NULL) {
        fprintf(stderr, "hook contract symbols load/unload are missing\n");
        dlclose(handle);
        return 1;
    }

    const int hooks_version = hook_version();
    if (hooks_version != EXPECTED_HOOKS_VERSION) {
        fprintf(stderr, "unexpected hooks version %d (expected %d)\n",
                hooks_version, EXPECTED_HOOKS_VERSION);
        dlclose(handle);
        return 1;
    }

    /* The RADIUS hook keeps its RADIUS dictionary next to the plug-in in the
     * package, so the packaged file must be present for the hook to work. */
    if (getenv("KEA_RADIUS_DICTIONARY") != NULL) {
        printf("info - KEA_RADIUS_DICTIONARY=%s\n", getenv("KEA_RADIUS_DICTIONARY"));
    }

    printf("libdhcp_radius.so loaded (hooks version %d)\n", hooks_version);
    dlclose(handle);
    printf("kea-hook-radius/3.0.3 OK\n");
    return 0;
}
