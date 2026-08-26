/* test_minplugin.c
 *
 * A minimal but fully valid LADSPA plugin, built by the test_package consumer
 * against the installed ladspa.h header. It proves the header is usable for
 * authoring plugins: it defines instantiate/connect_port/run/cleanup and
 * exports ladspa_descriptor(), the exact symbol a LADSPA host looks up via
 * dlsym().
 *
 * The plugin is a "pass-through": one audio in, one audio out. run() copies
 * the input block to the output so the descriptor can be exercised.
 */
#include <stdlib.h>
#include <string.h>

#include "ladspa.h"

#define PORT_IN  0
#define PORT_OUT 1
#define PORT_COUNT 2

static const unsigned long kUniqueID = 0x1000001UL;
static const char *kLabel = "passthrough";
static const char *kName = "Test Pass-Through";
static const char *kMaker = "ladspa-sdk test_package";
static const char *kCopyright = "None";

typedef struct {
    LADSPA_Data *in;
    LADSPA_Data *out;
} Instance;

static LADSPA_Handle instantiate(const LADSPA_Descriptor *desc,
                                 unsigned long sample_rate) {
    (void)desc; (void)sample_rate;
    Instance *h = (Instance *)calloc(1, sizeof(Instance));
    return (LADSPA_Handle)h;
}

static void connect_port(LADSPA_Handle inst, unsigned long port,
                         LADSPA_Data *loc) {
    Instance *h = (Instance *)inst;
    switch (port) {
    case PORT_IN:  h->in  = loc; break;
    case PORT_OUT: h->out = loc; break;
    }
}

static void run(LADSPA_Handle inst, unsigned long n) {
    Instance *h = (Instance *)inst;
    if (h->in && h->out && h->in != h->out)
        memcpy(h->out, h->in, n * sizeof(LADSPA_Data));
}

static void cleanup(LADSPA_Handle inst) {
    free(inst);
}

static const LADSPA_PortDescriptor kPortDescriptors[PORT_COUNT] = {
    LADSPA_PORT_INPUT | LADSPA_PORT_AUDIO,
    LADSPA_PORT_OUTPUT | LADSPA_PORT_AUDIO,
};
static const char *const kPortNames[PORT_COUNT] = { "Input", "Output" };
static const LADSPA_PortRangeHint kPortRangeHints[PORT_COUNT] = { {0,0,0}, {0,0,0} };

static LADSPA_Descriptor g_desc;

__attribute__((constructor))
static void init(void) {
    g_desc.UniqueID = kUniqueID;
    g_desc.Label = kLabel;
    g_desc.Properties = LADSPA_PROPERTY_HARD_RT_CAPABLE;
    g_desc.Name = kName;
    g_desc.Maker = kMaker;
    g_desc.Copyright = kCopyright;
    g_desc.PortCount = PORT_COUNT;
    g_desc.PortDescriptors = kPortDescriptors;
    g_desc.PortNames = kPortNames;
    g_desc.PortRangeHints = kPortRangeHints;
    g_desc.ImplementationData = NULL;
    g_desc.instantiate = instantiate;
    g_desc.connect_port = connect_port;
    g_desc.activate = NULL;
    g_desc.run = run;
    g_desc.run_adding = NULL;
    g_desc.set_run_adding_gain = NULL;
    g_desc.deactivate = NULL;
    g_desc.cleanup = cleanup;
}

/* Exported entry point a LADSPA host looks up via dlsym(). Marked
 * visibility("default") because the module is built with hidden visibility
 * (C_VISIBILITY_PRESET hidden in CMakeLists) — mirroring upstream's
 * gcc_exports.map, which exports ONLY ladspa_descriptor and hides everything
 * else. */
__attribute__((visibility("default")))
const LADSPA_Descriptor *ladspa_descriptor(unsigned long index) {
    return index == 0 ? &g_desc : NULL;
}
