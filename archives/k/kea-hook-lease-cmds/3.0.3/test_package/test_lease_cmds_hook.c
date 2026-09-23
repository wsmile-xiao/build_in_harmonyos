/*
 * Consumer test for kea-hook-lease-cmds.
 *
 * Loads the packaged Kea hook plug-in the way the Kea server does
 * (dlopen + dlsym) and checks the hook ABI contract (version/load/unload)
 * together with the lease-command callouts it exports, including the hook
 * framework version the plug-in was built against.
 */
#include <dlfcn.h>
#include <stdio.h>

/* Kea 3.0.3 src/lib/hooks/hooks.h: const int KEA_HOOKS_VERSION = 30003; */
#define EXPECTED_HOOKS_VERSION 30003

typedef int (*hook_version_fn)(void);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libdhcp_lease_cmds.so>\n", argv[0]);
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
    /* lease_cmds registers the lease4- and lease6- command callouts. */
    if (dlsym(handle, "lease4_add") == NULL ||
        dlsym(handle, "lease4_get") == NULL ||
        dlsym(handle, "lease4_get_page") == NULL ||
        dlsym(handle, "lease6_add") == NULL ||
        dlsym(handle, "lease6_get") == NULL ||
        dlsym(handle, "lease6_bulk_apply") == NULL ||
        dlsym(handle, "lease4_wipe") == NULL ||
        dlsym(handle, "leases4_committed") == NULL) {
        fprintf(stderr, "lease_cmds command callouts are missing\n");
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

    printf("libdhcp_lease_cmds.so loaded (hooks version %d)\n", hooks_version);
    dlclose(handle);
    printf("kea-hook-lease-cmds/3.0.3 OK\n");
    return 0;
}
