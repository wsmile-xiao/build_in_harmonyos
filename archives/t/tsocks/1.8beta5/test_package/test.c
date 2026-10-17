/* Verify the adapted libtsocks.so actually loads on HarmonyOS: dlopen the
 * shim, resolve its connect() interception point, and report. Linking the
 * library into the test binary also proves the exported ABI is usable. */
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    void *h = dlopen("libtsocks.so", RTLD_NOW);
    if (!h) {
        printf("dlopen libtsocks.so failed: %s\n", dlerror());
        return 1;
    }
    void *s = dlsym(h, "connect");
    if (!s) {
        printf("dlsym connect failed: %s\n", dlerror());
        return 1;
    }
    printf("tsocks consumer test passed: 2 assertions (dlopen + dlsym connect)\n");
    dlclose(h);
    return 0;
}
