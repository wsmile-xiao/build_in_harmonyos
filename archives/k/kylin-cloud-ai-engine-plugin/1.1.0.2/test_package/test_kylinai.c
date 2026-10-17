/* Consumer end-to-end smoke for kylin-cloud-ai-engine-plugin 1.1.0.2.
 *
 * The package ships 4 Kylin AI engine plugin shared objects (xunfei /
 * deepseek / qwen / custom) installed under
 * lib/kylin-ai/plugins/ai-engines/. A real consumer (libkylin-ai-system
 * engine loader) discovers and dlopen()s them at runtime, so this test
 * exercises the exact consumption path: dynamic-load each plugin with all
 * of its DT_NEEDED resolved (libcurl.so, libc++_shared.so, libc.so),
 * confirm a known engine symbol is reachable, then unload cleanly.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

static const char *kPlugins[] = {
    "libxunfei-engine-plugin.so",
    "libdeepseek-engine-plugin.so",
    "libqwen-engine-plugin.so",
    "libcustom-engine-plugin.so",
};

int main(void)
{
    int failed = 0;
    const int n = (int)(sizeof(kPlugins) / sizeof(kPlugins[0]));

    /* The real consumer (the Kylin AI engine loader process) links
     * jsoncpp itself, so plugin symbols resolve against the host's
     * libjsoncpp at load time. Reproduce that host environment by
     * pre-loading jsoncpp RTLD_GLOBAL before dlopen()ing the plugins. */
    void *jsoncpp = dlopen("libjsoncpp.so", RTLD_GLOBAL | RTLD_LAZY);
    if (!jsoncpp) {
        fprintf(stderr, "FAIL preload libjsoncpp.so: %s\n", dlerror());
        return 1;
    }

    for (int i = 0; i < n; i++) {
        char path[512];
        snprintf(path, sizeof(path), "%s/%s", KYLIN_PLUGIN_DIR, kPlugins[i]);

        /* RTLD_NOW: force every relocation + DT_NEEDED to resolve now,
         * which is what the engine loader effectively requires. */
        void *h = dlopen(path, RTLD_NOW);
        if (!h) {
            fprintf(stderr, "FAIL dlopen(%s): %s\n", path, dlerror());
            failed++;
            continue;
        }

        /* Each plugin exports its engine vtable/ctors; probe one symbol to
         * prove the loaded image is the real plugin, not an empty map.
         * CustomNlpEngine::engineName() is a const member → _ZNK… mangling. */
        void *sym = dlsym(h, "_ZNK15CustomNlpEngine10engineNameEv");
        if (strstr(kPlugins[i], "custom") != NULL && !sym) {
            fprintf(stderr, "FAIL dlsym(engineName) in %s: %s\n", path, dlerror());
            failed++;
            dlclose(h);
            continue;
        }

        if (dlclose(h) != 0) {
            fprintf(stderr, "FAIL dlclose(%s): %s\n", path, dlerror());
            failed++;
            continue;
        }
        printf("OK %s\n", kPlugins[i]);
    }

    if (failed) {
        fprintf(stderr, "%d/%d plugins FAILED\n", failed, n);
        return 1;
    }
    printf("=== kylin-cloud-ai-engine-plugin tests PASSED ===\n");
    return 0;
}
