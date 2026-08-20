#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* LV2 descriptor entry point - the standard symbol exported by every LV2 plugin .so */
typedef struct {
    const char *URI;
    void *(*instantiate)(void *descriptor, double sample_rate,
                         const char *bundle_path, const void *features);
    void (*connect_port)(void *instance, unsigned long port, void *data);
    void (*activate)(void *instance);
    void (*run)(void *instance, unsigned long n_samples);
    void (*deactivate)(void *instance);
    void (*cleanup)(void *instance);
    const void *(*extension_data)(const char *uri);
} LV2_Descriptor_Test;

/* dlopen the built artyfx.so and verify it exports lv2_descriptor */
int main(void) {
    /* Try multiple candidate paths for the LV2 plugin */
    const char *paths[] = {
        "lib/lv2/artyfx.lv2/artyfx.so",
        "lib/artyfx.so",
        NULL
    };
    void *handle = NULL;
    int i;
    for (i = 0; paths[i]; i++) {
        handle = dlopen(paths[i], RTLD_LAZY | RTLD_LOCAL);
        if (handle) break;
    }
    /* Try the env var set by test_package conanfile */
    if (!handle) {
        const char *env_path = getenv("ARTYFX_SO_PATH");
        if (env_path) {
            handle = dlopen(env_path, RTLD_LAZY | RTLD_LOCAL);
        }
    }
    if (!handle) {
        fprintf(stderr, "FAIL: cannot dlopen artyfx.so: %s\n", dlerror());
        return 1;
    }

    /* LV2 plugins export: const LV2_Descriptor* lv2_descriptor(uint32_t index) */
    typedef const void *(*lv2_descriptor_fn)(unsigned long index);
    lv2_descriptor_fn descriptor_fn = (lv2_descriptor_fn)dlsym(handle, "lv2_descriptor");
    if (!descriptor_fn) {
        fprintf(stderr, "FAIL: lv2_descriptor symbol not found: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    /* Query first plugin descriptor (index 0) */
    const void *desc = descriptor_fn(0);
    if (!desc) {
        fprintf(stderr, "FAIL: lv2_descriptor(0) returned NULL\n");
        dlclose(handle);
        return 1;
    }

    /* Verify the URI field is set (non-NULL, non-empty) */
    const LV2_Descriptor_Test *ld = (const LV2_Descriptor_Test *)desc;
    if (!ld->URI || strlen(ld->URI) == 0) {
        fprintf(stderr, "FAIL: plugin URI is empty\n");
        dlclose(handle);
        return 1;
    }

    printf("PASS: artyfx.so loaded, lv2_descriptor found, URI = %s\n", ld->URI);

    /* Query more plugins (index 1, 2, ...) until NULL */
    int count = 1;
    while (descriptor_fn(count) != NULL) {
        count++;
    }
    printf("PASS: found %d LV2 plugins in artyfx.so\n", count);

    dlclose(handle);
    return 0;
}
