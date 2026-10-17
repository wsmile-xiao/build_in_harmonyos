/* gst-plugins-bad consumer test.
 *
 * The binary links against the packaged libraries (validated at build
 * time), and at startup the dynamic loader maps every NEEDED library
 * (validating their OHOS ELF signatures). Calling gst_init() from a
 * consumer is not possible here: the conan glib2/gstreamer packages are
 * static-only, so each packaged shared library embeds its own copy of
 * glib/gstreamer and gst_init() would mix per-DSO type registries and
 * deadlock (same reason the gst-libav test verifies via dlopen/dlsym).
 * Runtime verification therefore dlopen()s the insertbin library and
 * checks its public API symbol.
 */
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    void *handle = dlopen("libgstinsertbin-1.0.so.0", RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    void *sym = dlsym(handle, "gst_insert_bin_new");
    if (!sym) {
        fprintf(stderr, "gst_insert_bin_new not found\n");
        dlclose(handle);
        return 1;
    }
    printf("gst-plugins-bad test: libgstinsertbin-1.0 loaded, gst_insert_bin_new OK\n");
    printf("gst-plugins-bad test: PASS\n");
    dlclose(handle);
    return 0;
}
