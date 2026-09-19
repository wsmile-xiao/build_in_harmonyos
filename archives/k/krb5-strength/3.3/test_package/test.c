#include <dlfcn.h>
#include <stdio.h>

/* Loads the krb5 pwqual plugin and verifies the MIT plugin interface
 * entry point is exported. RTLD_NOW forces full symbol resolution, so a
 * successful dlopen also proves the plugin's krb5 shared-library
 * dependencies (libkrb5.so, libk5crypto.so, libcom_err.so) resolve. */
int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <plugin-path>\n", argv[0]);
        return 2;
    }
    void *h = dlopen(argv[1], RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    void *sym = dlsym(h, "pwqual_strength_initvt");
    if (!sym) {
        fprintf(stderr, "dlsym(pwqual_strength_initvt) failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    printf("krb5-strength pwqual plugin loaded, interface OK\n");
    dlclose(h);
    return 0;
}
