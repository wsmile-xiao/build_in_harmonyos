/*
 * Consumer test for webp-pixbuf-loader 0.2.7
 *
 * This test exercises the pixbufloader-webp shared module by loading it
 * with dlopen and calling its fill_info() entry point to verify that
 * the module is correctly built and exports the expected GDK Pixbuf
 * loader interface.
 *
 * The fill_info() function fills a GdkPixbufFormat struct with the
 * loader's metadata (name, signature, mime types, extensions).
 * We check that the format name is "webp".
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Minimal forward declarations — avoid pulling in gdk-pixbuf headers
 * in the test_package to keep the dependency surface small.  We only
 * need the fill_info() entry point which fills a struct whose first
 * field is a char* (the format name). */
typedef struct {
    char *name;
    /* remaining fields are irrelevant for this test */
    void *signature;
    char *description;
    char **mime_types;
    char **extensions;
    int flags;
    char *license;
} GdkPixbufFormat;

/* Function pointer type for fill_info() */
typedef void (*FillInfoFunc)(GdkPixbufFormat *info);

static int checks = 0;

static int require_true(int condition, const char *message)
{
    checks++;
    if (!condition) {
        fprintf(stderr, "check %d failed: %s\n", checks, message);
        return 0;
    }
    return 1;
}

int main(void)
{
    int ret = 0;
    void *handle = NULL;
    FillInfoFunc fill_info = NULL;
    GdkPixbufFormat info;
    const char *module_path = NULL;

    /* The module is installed at lib/gdk-pixbuf-2.0/loaders/libpixbufloader-webp.so
     * Conan sets WEBP_PIXBUF_LOADER_MODULE_DIR in the run environment. */
    module_path = getenv("WEBP_PIXBUF_LOADER_MODULE_DIR");
    if (!module_path || !module_path[0]) {
        /* Fallback: try common paths relative to the package */
        const char *candidates[] = {
            "lib/gdk-pixbuf-2.0/loaders/libpixbufloader-webp.so",
            "lib/pixbufloader-webp.so",
            "lib/libpixbufloader-webp.so",
            NULL,
        };
        const char *pkg_root = getenv("WEBP_PIXBUF_LOADER_ROOT");
        if (pkg_root && pkg_root[0]) {
            for (int i = 0; candidates[i]; i++) {
                char full[4096];
                snprintf(full, sizeof(full), "%s/%s", pkg_root, candidates[i]);
                if (access(full, F_OK) == 0) {
                    module_path = strdup(full);
                    break;
                }
            }
        }
        if (!module_path) {
            /* Last resort: just use the relative path */
            module_path = "lib/gdk-pixbuf-2.0/loaders/libpixbufloader-webp.so";
        }
    }

    /* 1. dlopen the module — exercises the actual built .so */
    handle = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
    if (!require_true(handle != NULL, "dlopen pixbufloader-webp module")) {
        fprintf(stderr, "dlopen error: %s (path: %s)\n", dlerror(), module_path);
        return 1;
    }

    /* 2. dlsym for fill_info — verifies the module exports the expected symbol */
    *(void **)(&fill_info) = dlsym(handle, "fill_info");
    if (!require_true(fill_info != NULL, "dlsym fill_info")) {
        fprintf(stderr, "dlsym error: %s\n", dlerror());
        dlclose(handle);
        return 2;
    }

    /* 3. Call fill_info — exercises the module's actual API */
    memset(&info, 0, sizeof(info));
    fill_info(&info);

    /* 4. Verify the format name is "webp" */
    if (!require_true(info.name != NULL, "fill_info sets format name")) {
        dlclose(handle);
        return 3;
    }
    if (!require_true(strcmp(info.name, "webp") == 0, "format name is 'webp'")) {
        fprintf(stderr, "unexpected format name: %s\n", info.name);
        ret = 4;
    }

    /* 5. Verify the description is set */
    if (!require_true(info.description != NULL && info.description[0] != '\0',
                      "fill_info sets description")) {
        ret = 5;
    }

    dlclose(handle);
    printf("webp-pixbuf-loader consumer checks: %d/5 passed\n", checks);
    return ret;
}
