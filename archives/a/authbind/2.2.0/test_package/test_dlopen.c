/*
 * test_package/test_dlopen.c — dlopen closure probe for libauthbind.so.
 *
 * Opens the packaged libauthbind.so with dlopen() and asserts that the
 * interposition symbol "bind" resolves (dlsym) — proving the shared object's
 * dynamic symbol table survived the OHOS link, and that libc/libdl closure
 * needed by authbind is intact.  Does not bind any socket.
 */
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <libauthbind.so>\n", argv[0]);
        return 2;
    }
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    dlerror();
    void *sym = dlsym(h, "bind");
    const char *err = dlerror();
    if (err) {
        fprintf(stderr, "dlsym(bind) failed: %s\n", err);
        return 1;
    }
    if (!sym) {
        fprintf(stderr, "dlsym(bind) returned NULL\n");
        return 1;
    }
    printf("AUTHBIND_DLOPEN_BIND_SYMBOL_OK %s\n", argv[1]);
    dlclose(h);
    return 0;
}
