#include <stdio.h>
#include <dlfcn.h>

int main(void) {
    const char *lib_path = JNA_LIB_PATH;
    void *handle = dlopen(lib_path, RTLD_LAZY | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    /* Check for JNI_OnLoad symbol (standard JNI entry point) */
    void *onload = dlsym(handle, "JNI_OnLoad");
    if (!onload) {
        fprintf(stderr, "JNI_OnLoad not found\n");
        dlclose(handle);
        return 2;
    }

    /* Check for Java_com_sun_jna_Native_initIDs */
    void *initids = dlsym(handle, "Java_com_sun_jna_Native_initIDs");
    if (!initids) {
        fprintf(stderr, "Java_com_sun_jna_Native_initIDs not found\n");
        dlclose(handle);
        return 3;
    }

    dlclose(handle);
    puts("libjnidispatch.so: dlopen + symbol check passed");
    return 0;
}
