/*
 * Consumer test for kea-hook-pgsql.
 *
 * Loads the packaged Kea hook plug-in the way the Kea server does
 * (dlopen + dlsym) and checks the hook ABI contract (version/load/unload,
 * multi-threading compatibility) together with the DHCP server callouts the
 * plug-in registers for kea-dhcp4/kea-dhcp6 (dhcp4_srv_configured,
 * dhcp6_srv_configured), including the hook framework version it was built
 * against.  No PostgreSQL server is needed: load() only registers the
 * PostgreSQL back-end factories.
 */
#include <dlfcn.h>
#include <stdio.h>

/* Kea 3.0.3 src/lib/hooks/hooks.h: const int KEA_HOOKS_VERSION = 30003; */
#define EXPECTED_HOOKS_VERSION 30003

typedef int (*hook_version_fn)(void);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libdhcp_pgsql.so>\n", argv[0]);
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
    if (dlsym(handle, "multi_threading_compatible") == NULL) {
        fprintf(stderr, "multi_threading_compatible entry point is missing\n");
        dlclose(handle);
        return 1;
    }
    if (dlsym(handle, "dhcp4_srv_configured") == NULL ||
        dlsym(handle, "dhcp6_srv_configured") == NULL) {
        fprintf(stderr, "pgsql hook server callouts are missing\n");
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

    printf("libdhcp_pgsql.so loaded (hooks version %d)\n", hooks_version);
    dlclose(handle);
    printf("kea-hook-pgsql/3.0.3 OK\n");
    return 0;
}
