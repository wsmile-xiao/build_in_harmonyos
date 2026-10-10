#include <dlfcn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ladspa.h"
#include "m_pd.h"

static int failures;
static int checks;
static int class_calls;
static int method_calls;
static int search_callbacks;

#define CHECK(condition, message) do {                                      \
    checks++;                                                               \
    if (!(condition)) {                                                     \
        fprintf(stderr, "not ok %d - %s\n", checks, message);             \
        failures++;                                                         \
    } else {                                                                \
        printf("ok %d - %s\n", checks, message);                          \
    }                                                                       \
} while (0)

/* Minimal Pd runtime ABI supplied by the executable, as the real Pd binary
 * does for externals loaded with dlopen(). */
t_symbol *gensym(const char *name) {
    static t_symbol symbols[32];
    static char names[32][64];
    static size_t used;
    size_t i;
    for (i = 0; i < used; i++)
        if (!strcmp(symbols[i].s_name, name))
            return &symbols[i];
    if (used >= 32)
        return NULL;
    snprintf(names[used], sizeof names[used], "%s", name);
    symbols[used].s_name = names[used];
    return &symbols[used++];
}

void nullfn(void) {}
t_class *class_new(t_symbol *name, t_newmethod newmethod, t_method freemethod,
                   size_t size, int flags, t_atomtype arg1, ...) {
    static uintptr_t fake_class;
    (void)name; (void)newmethod; (void)freemethod; (void)size; (void)flags; (void)arg1;
    class_calls++;
    return (t_class *)&fake_class;
}
void class_addmethod(t_class *c, t_method fn, t_symbol *selector,
                     t_atomtype arg1, ...) {
    (void)c; (void)fn; (void)selector; (void)arg1;
    method_calls++;
}
t_pd *pd_new(t_class *c) { (void)c; return NULL; }
t_inlet *inlet_new(t_object *owner, t_pd *dest, t_symbol *s1, t_symbol *s2) {
    (void)owner; (void)dest; (void)s1; (void)s2; return (t_inlet *)(uintptr_t)1;
}
void inlet_free(t_inlet *x) { (void)x; }
t_outlet *outlet_new(t_object *owner, t_symbol *s) {
    (void)owner; (void)s; return (t_outlet *)(uintptr_t)1;
}
void outlet_anything(t_outlet *x, t_symbol *s, int argc, t_atom *argv) {
    (void)x; (void)s; (void)argc; (void)argv;
}
void outlet_free(t_outlet *x) { (void)x; }
void dsp_addv(t_perfroutine fn, int count, t_int *vector) {
    (void)fn; (void)count; (void)vector;
}
t_float sys_getsr(void) { return 48000.0f; }
void pd_error(const void *object, const char *format, ...) {
    (void)object; (void)format;
}
void post(const char *format, ...) { (void)format; }
void verbose(int level, const char *format, ...) { (void)level; (void)format; }

typedef void (*setup_fn)(void);
typedef void *(*load_fn)(const char *);
typedef void (*unload_fn)(void *);
typedef const LADSPA_Descriptor *(*find_fn)(void *, const char *, const char *);
typedef void (*search_callback_fn)(const char *, void *, LADSPA_Descriptor_Function, void *);
typedef void (*search_fn)(search_callback_fn, void *);

static void count_plugin(const char *filename, void *handle,
                         LADSPA_Descriptor_Function descriptor, void *user_data) {
    (void)filename; (void)handle; (void)user_data;
    if (descriptor && descriptor(0))
        search_callbacks++;
}

int main(int argc, char **argv) {
    void *module;
    void *ladspa;
    setup_fn setup;
    load_fn load_plugin;
    unload_fn unload_plugin;
    find_fn find_plugin;
    search_fn search_plugins;
    LADSPA_Descriptor_Function descriptor_function;
    const LADSPA_Descriptor *descriptor;
    const LADSPA_Descriptor *found;
    LADSPA_Handle instance;
    LADSPA_Data gain = 2.0f;
    LADSPA_Data input[4] = {0.25f, -0.5f, 1.0f, 0.0f};
    LADSPA_Data output[4] = {0};
    char *slash;
    char ladspa_dir[4096];

    CHECK(argc == 3, "test receives the packaged Pd external and LADSPA fixture");
    if (argc != 3)
        return 1;
    module = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    CHECK(module != NULL, "packaged plugin~ external loads with RTLD_NOW");
    if (!module) {
        fprintf(stderr, "dlopen: %s\n", dlerror());
        return 1;
    }

    setup = (setup_fn)dlsym(module, "plugin_tilde_setup");
    load_plugin = (load_fn)dlsym(module, "loadLADSPAPluginLibrary");
    unload_plugin = (unload_fn)dlsym(module, "unloadLADSPAPluginLibrary");
    find_plugin = (find_fn)dlsym(module, "findLADSPAPluginDescriptor");
    search_plugins = (search_fn)dlsym(module, "LADSPAPluginSearch");
    CHECK(setup != NULL, "Pure Data setup entry point is exported");
    CHECK(load_plugin != NULL, "LADSPA loader helper is exported");
    CHECK(unload_plugin != NULL, "LADSPA unload helper is exported");
    CHECK(find_plugin != NULL, "LADSPA descriptor helper is exported");
    CHECK(search_plugins != NULL, "LADSPA path search helper is exported");

    setup();
    CHECK(class_calls == 1, "setup registers exactly one Pure Data class");
    CHECK(method_calls == 8, "setup registers all eight plugin~ methods");

    snprintf(ladspa_dir, sizeof ladspa_dir, "%s", argv[2]);
    slash = strrchr(ladspa_dir, '/');
    CHECK(slash != NULL, "LADSPA fixture uses an absolute package path");
    if (slash)
        *slash = '\0';
    CHECK(setenv("LADSPA_PATH", ladspa_dir, 1) == 0, "LADSPA_PATH is configured");
    search_plugins(count_plugin, NULL);
    CHECK(search_callbacks >= 1, "LADSPA path search discovers a real plugin");

    ladspa = load_plugin(argv[2]);
    CHECK(ladspa != NULL, "plugin~ loads the packaged LADSPA library");
    descriptor_function = ladspa ?
        (LADSPA_Descriptor_Function)dlsym(ladspa, "ladspa_descriptor") : NULL;
    CHECK(descriptor_function != NULL, "LADSPA descriptor function resolves");
    descriptor = descriptor_function ? descriptor_function(0) : NULL;
    CHECK(descriptor != NULL, "LADSPA mono amplifier descriptor exists");
    CHECK(descriptor && !strcmp(descriptor->Label, "amp_mono"),
          "fixture descriptor has the expected amp_mono label");
    found = descriptor ? find_plugin(ladspa, argv[2], descriptor->Label) : NULL;
    CHECK(found == descriptor, "plugin~ finds the descriptor by label");

    instance = found ? found->instantiate(found, 48000) : NULL;
    CHECK(instance != NULL, "LADSPA amplifier instance is created");
    if (instance) {
        found->connect_port(instance, 0, &gain);
        found->connect_port(instance, 1, input);
        found->connect_port(instance, 2, output);
        found->run(instance, 4);
    }
    CHECK(output[0] == 0.5f && output[1] == -1.0f &&
          output[2] == 2.0f && output[3] == 0.0f,
          "loaded LADSPA plugin processes an audio block correctly");
    if (instance)
        found->cleanup(instance);
    if (ladspa)
        unload_plugin(ladspa);
    CHECK(dlclose(module) == 0, "packaged Pure Data external unloads cleanly");

    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
