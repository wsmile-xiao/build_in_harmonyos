/* Target 2 - run-time verification for the zephyr/3.1.2 package.
 *
 * Loads the packaged shared object by absolute path (argv[1], resolved by
 * conanfile.py test() from the dependency's package folder and its SONAME) and
 * obtains the public entry points with dlsym().  This is the run-time check
 * that HarmonyOS actually allows: the loader ignores LD_LIBRARY_PATH,
 * DT_RUNPATH, $ORIGIN and LD_PRELOAD and only searches its namespace paths
 * (knowledge/doc/E088), so a dlopen() with an absolute path is the way a
 * consumer reaches a library that is not installed into a namespace directory.
 *
 * This target links nothing from the package: <zephyr/zephyr.h> is taken from
 * the interface include directories of zephyr::zephyr, and NO library is
 * linked, so the produced executable carries no DT_NEEDED for libzephyr and can
 * always be started.  All assertions of the consumer test run against the
 * dlsym()ed symbols (see zephyr_consumer.h).
 */
#include <dlfcn.h>

#include "zephyr_consumer.h"

/* dlerror() clears the error state on every call, so the message has to be
 * fetched exactly once into a local before being handed to the reporter. */
#define RESOLVE(field, symbol)                                       \
    do {                                                             \
        *(void **)(&api.field) = dlsym(handle, symbol);               \
        if (api.field == NULL) {                                      \
            const char *err = dlerror();                              \
            fprintf(stderr, "FAIL - dlsym(%s): %s\n", symbol,         \
                    err ? err : "symbol not found");                  \
            dlclose(handle);                                          \
            return 1;                                                 \
        }                                                             \
    } while (0)

int main(int argc, char **argv)
{
    void *handle;
    struct zephyr_api api;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <absolute path to libzephyr.so.4>\n", argv[0]);
        return 2;
    }

    memset(&api, 0, sizeof(api));

    handle = dlopen(argv[1], RTLD_NOW);
    if (handle == NULL) {
        const char *err = dlerror();
        fprintf(stderr, "FAIL - dlopen(%s): %s\n", argv[1],
                err ? err : "unknown error");
        return 1;
    }

    printf("dlopen(%s) -> OK\n", argv[1]);

    RESOLVE(initialize, "ZInitialize");
    RESOLVE(get_realm, "ZGetRealm");
    RESOLVE(get_sender, "ZGetSender");
    RESOLVE(get_fd, "ZGetFD");
    RESOLVE(compare_uid, "ZCompareUID");
    RESOLVE(format_notice, "ZFormatNotice");
    RESOLVE(parse_notice, "ZParseNotice");
    RESOLVE(free_notice, "ZFreeNotice");

    {
        int rc = zephyr_run_consumer_checks(&api, "dlopen(absolute path)");
        dlclose(handle);
        return rc;
    }
}
