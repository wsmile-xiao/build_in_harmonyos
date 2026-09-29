/*
 * Consumer test for libopenraw-pixbuf-loader 0.3.7
 *
 * Exercises the actually-built-and-packaged gdk-pixbuf module
 * (libopenraw_pixbuf.so) the same way gdk-pixbuf itself does: dlopen() it
 * and call its two G_MODULE_EXPORT entry points.
 *
 *   1. negative control: dlopen() of a non-existent path must fail
 *   2. dlopen() the packaged module
 *   3. dlsym() the fill_info / fill_vtable entry points
 *   4. fill_info()  -> the format must be "Digital camera RAW" with the
 *                      upstream RAW extension / mime-type sets
 *   5. fill_vtable() -> the incremental-load entry points must be wired up
 *   6. negative control: dlsym() of a bogus symbol must return NULL
 *
 * The GdkPixbufFormat / GdkPixbufModule declarations come from the real
 * gdk-pixbuf backend headers (GDK_PIXBUF_ENABLE_BACKEND), so the struct
 * offsets used here are guaranteed to match the module's build.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GDK_PIXBUF_ENABLE_BACKEND
#include <gdk-pixbuf/gdk-pixbuf-io.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

typedef void (*fill_info_t)(GdkPixbufFormat *info);
typedef void (*fill_vtable_t)(GdkPixbufModule *module);

static int checks = 0;
static int failures = 0;

static void check(int condition, const char *message)
{
    checks++;
    if (condition) {
        printf("ok %d - %s\n", checks, message);
    } else {
        failures++;
        printf("not ok %d - %s\n", checks, message);
    }
}

static int has_str(char **array, const char *want)
{
    int i;
    if (!array) {
        return 0;
    }
    for (i = 0; array[i]; i++) {
        if (strcmp(array[i], want) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(void)
{
    const char *module_path = getenv("OPENRAW_PIXBUF_MODULE");
    void *handle = NULL;
    void *missing = NULL;
    fill_info_t fill_info = NULL;
    fill_vtable_t fill_vtable = NULL;
    GdkPixbufFormat info;
    GdkPixbufModule module;
    int ext_count = 0;

    if (!module_path || !module_path[0]) {
        fprintf(stderr, "OPENRAW_PIXBUF_MODULE is not set\n");
        return 2;
    }

    /* 1. negative control: a non-existent module must not load */
    missing = dlopen("/nonexistent/libdoes_not_exist_xyz.so", RTLD_NOW | RTLD_LOCAL);
    check(missing == NULL, "negative control: dlopen() of a missing module fails");
    if (missing) {
        dlclose(missing);
    }

    /* 2. dlopen the module that was built and packaged */
    handle = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen failed for %s: %s\n", module_path, dlerror());
        check(0, "dlopen libopenraw_pixbuf.so module");
        printf("1..%d\n", checks);
        return 1;
    }
    check(1, "dlopen libopenraw_pixbuf.so module");

    /* 3. the two G_MODULE_EXPORT entry points must exist */
    *(void **)(&fill_info) = dlsym(handle, "fill_info");
    *(void **)(&fill_vtable) = dlsym(handle, "fill_vtable");
    check(fill_info != NULL, "dlsym fill_info");
    check(fill_vtable != NULL, "dlsym fill_vtable");
    if (!fill_info || !fill_vtable) {
        dlclose(handle);
        printf("1..%d\n", checks);
        return 1;
    }

    /* 4. fill_info() must describe the RAW loader */
    memset(&info, 0, sizeof(info));
    fill_info(&info);
    check(info.name != NULL && strcmp(info.name, "Digital camera RAW") == 0,
          "fill_info() name == \"Digital camera RAW\"");
    if (info.name) {
        printf("# format name: %s\n", info.name);
    }
    check(has_str(info.extensions, "cr2"), "extensions contain \"cr2\"");
    check(has_str(info.extensions, "dng"), "extensions contain \"dng\"");
    check(has_str(info.mime_types, "image/x-canon-cr2"),
          "mime_types contain \"image/x-canon-cr2\"");
    if (info.extensions) {
        while (info.extensions[ext_count]) {
            ext_count++;
        }
    }
    check(ext_count == 10, "fill_info() declares exactly 10 RAW extensions");

    /* 5. fill_vtable() must wire up incremental loading */
    memset(&module, 0, sizeof(module));
    fill_vtable(&module);
    check(module.begin_load != NULL, "fill_vtable() sets begin_load");
    check(module.stop_load != NULL, "fill_vtable() sets stop_load");
    check(module.load_increment != NULL, "fill_vtable() sets load_increment");
    check(module.load == NULL,
          "fill_vtable() leaves load == NULL (matches upstream)");

    /* 6. negative control on symbol lookup */
    check(dlsym(handle, "fill_vtable_bogus_symbol") == NULL,
          "negative control: dlsym() of a bogus symbol returns NULL");

    dlclose(handle);

    printf("1..%d\n", checks);
    printf("# %d/%d checks passed\n", checks - failures, checks);
    return failures == 0 ? 0 : 1;
}
