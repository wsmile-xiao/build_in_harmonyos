#include <stdio.h>
#include <dlfcn.h>

int main(int argc, char *argv[]) {
    const char *plugin_path = (argc > 1) ? argv[1] : NULL;
    if (!plugin_path) {
        fprintf(stderr, "Usage: %s <plugin_path>\n", argv[0]);
        return 1;
    }
    void *handle = dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) { fprintf(stderr, "dlopen failed: %s\n", dlerror()); return 1; }
    void *get_desc = dlsym(handle, "gst_plugin_libav_get_desc");
    void *reg = dlsym(handle, "gst_plugin_libav_register");
    if (!get_desc || !reg) { fprintf(stderr, "missing symbols\n"); dlclose(handle); return 1; }
    printf("gst-libav plugin loaded, symbols OK\n");
    printf("gst-libav test: PASS\n");
    dlclose(handle);
    return 0;
}
