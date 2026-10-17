/*
 * check_libscanmem.c -- HarmonyOS-specific consumer check for libscanmem.
 *
 * dlopen()s the *packaged* libscanmem.so.1 and dlsym()s the public API that
 * libtool's `-export-symbols-regex '^sm_|^show_'` is supposed to keep visible.
 * This is the assertion that is specific to the OHOS port: it exercises the
 * libtool-generated version script under the OHOS dynamic linker and confirms
 * the shared object actually loads (its own dependencies resolve) on the
 * target, which a --version smoke test of the CLI never proves.
 *
 * Built by test_package/conanfile.py and run by test_scanmem.sh (check t7).
 * Prints "LIBCHECK <key>=<value>" lines; the shell harness asserts on them.
 */

#include <dlfcn.h>
#include <stdio.h>

typedef const char *(*get_version_fn)(void);
typedef void (*print_version_fn)(void *);

int main(int argc, char **argv)
{
    const char *path = (argc >= 2) ? argv[1] : "libscanmem.so.1";
    void *h;
    const char *(*get_version)(void);
    void (*print_version)(void *);
    const char *ver;
    const char *err;

    h = dlopen(path, RTLD_NOW);
    if (h == NULL) {
        err = dlerror();
        printf("LIBCHECK dlopen=fail detail=%s\n", err ? err : "unknown");
        return 1;
    }
    printf("LIBCHECK dlopen=ok\n");

    dlerror();
    *(void **) (&get_version) = dlsym(h, "sm_get_version");
    err = dlerror();
    if (err != NULL || get_version == NULL) {
        printf("LIBCHECK sm_get_version=missing detail=%s\n", err ? err : "null");
        dlclose(h);
        return 1;
    }
    printf("LIBCHECK sm_get_version=present\n");

    dlerror();
    *(void **) (&print_version) = dlsym(h, "sm_printversion");
    err = dlerror();
    if (err != NULL || print_version == NULL) {
        printf("LIBCHECK sm_printversion=missing detail=%s\n", err ? err : "null");
        dlclose(h);
        return 1;
    }
    printf("LIBCHECK sm_printversion=present\n");

    /* scanmem.c: sm_get_version() returns PACKAGE_VERSION verbatim. */
    ver = get_version();
    if (ver == NULL || ver[0] == '\0') {
        printf("LIBCHECK version=empty\n");
        dlclose(h);
        return 1;
    }
    printf("LIBCHECK version=%s\n", ver);

    /* sm_printversion writes "libscanmem version <ver>" to the given FILE*. */
    print_version(stdout);
    fflush(stdout);
    printf("\n");

    dlclose(h);
    return 0;
}
