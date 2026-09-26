/*
 * HarmonyOS-specific guard for libproperties 1.1.2.
 *
 * On this platform CMake reports CMAKE_SYSTEM_NAME=HarmonyOS but ships no
 * Modules/Platform/HarmonyOS.cmake, so CMAKE_SHARED_LIBRARY_SONAME_C_FLAG is
 * undefined unless the recipe injects it.  Without that fix the installed tree
 * contains a single bare "libproperties.so" (no DT_SONAME, no versioned file
 * names) and consumers record a path-form DT_NEEDED that only resolves inside
 * the build directory — W3 reports it as "L5a: ... 缺少 DT_SONAME".
 *
 * This test therefore loads the library by its bare versioned soname.  It only
 * succeeds when the versioned file exists and the shared object is usable, and
 * it fails on the unadapted build with:
 *     dlopen failed: Error loading shared library libproperties.so.1
 */
#include <dlfcn.h>
#include <stdio.h>

int main(void)
{
    void* handle = dlopen("libproperties.so.1", RTLD_NOW | RTLD_LOCAL);

    if (handle == NULL) {
        fprintf(stderr, "test_libproperties_soname: FAIL — dlopen(\"libproperties.so.1\"): %s\n",
            dlerror());
        return 1;
    }
    if (dlsym(handle, "properties_parse") == NULL) {
        fprintf(stderr, "test_libproperties_soname: FAIL — properties_parse not exported: %s\n",
            dlerror());
        dlclose(handle);
        return 1;
    }
    dlclose(handle);

    printf("test_libproperties_soname: OK (libproperties.so.1 resolved by bare soname)\n");
    return 0;
}
