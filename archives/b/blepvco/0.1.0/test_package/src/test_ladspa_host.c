/* dlopen smoke host for LADSPA plugins (blepvco test_package).
 *
 * Loads the packaged plugin .so, walks ladspa_descriptor(), and exercises
 * instantiate/activate/run/deactivate/cleanup on every descriptor with all
 * ports connected (audio inputs included — LADSPA has no NULL-port
 * convention, and blepvco's SYNCIN audio-input port segfaults if left
 * disconnected). Exit 0 only when exactly 3 descriptors run cleanly
 * (blepvco exports Sync-Saw-VCO / Sync-Rect-VCO / Sync-Tri-VCO).
 */
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <ladspa.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s <plugin.so>\n", argv[0]); return 2; }
    void *handle = dlopen(argv[1], RTLD_NOW);
    if (!handle) { fprintf(stderr, "FAIL: dlopen: %s\n", dlerror()); return 1; }
    LADSPA_Descriptor_Function fn =
        (LADSPA_Descriptor_Function)dlsym(handle, "ladspa_descriptor");
    if (!fn) { fprintf(stderr, "FAIL: no ladspa_descriptor\n"); return 1; }
    int count = 0;
    for (unsigned long i = 0; ; i++) {
        const LADSPA_Descriptor *d = fn(i);
        if (!d) break;
        count++;
        printf("plugin %lu: id=%lu label=%s ports=%lu\n",
               i, d->UniqueID, d->Label ? d->Label : "(null)", d->PortCount);
        LADSPA_Handle inst = d->instantiate(d, 48000);
        if (!inst) { fprintf(stderr, "FAIL: instantiate %s\n", d->Label); return 1; }
        LADSPA_Data ctl[1] = { 1.0f };
        LADSPA_Data io[64];
        memset(io, 0, sizeof(io));
        for (unsigned long p = 0; p < d->PortCount; p++) {
            LADSPA_PortDescriptor pd = d->PortDescriptors[p];
            if (LADSPA_IS_PORT_INPUT(pd) && LADSPA_IS_PORT_CONTROL(pd)) {
                if (d->connect_port) d->connect_port(inst, p, ctl);
            } else {
                /* audio in/out and control outputs: connect a real buffer */
                if (d->connect_port) d->connect_port(inst, p, io);
            }
        }
        if (d->activate) d->activate(inst);
        if (d->run) d->run(inst, 64);
        if (d->deactivate) d->deactivate(inst);
        if (d->cleanup) d->cleanup(inst);
        printf("  instantiate/activate/run/deactivate/cleanup OK\n");
    }
    dlclose(handle);
    if (count != 3) {
        fprintf(stderr, "FAIL: expected 3 descriptors, got %d\n", count);
        return 1;
    }
    printf("PASS: %d LADSPA descriptors exercised\n", count);
    return 0;
}
