// HarmonyOS-specific consumer test for the rev (REV LADSPA plugins) package.
// The upstream project ships no test suite, so this test_package performs the
// HarmonyOS-side verification required by R34/R51:
//   1. the LADSPA plugin .so is installed and loadable via dlopen;
//   2. it exports the LADSPA descriptor symbol and self-describes correctly
//      (plugin count, unique LADSPA IDs, valid port counts);
//   3. the plugin's instantiate/run/cleanup lifecycle works on an OHOS
//      aarch64 process, processing a real audio buffer.
#include <dlfcn.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "ladspa.h"

typedef const LADSPA_Descriptor *(*ladspa_descriptor_fn)(unsigned long);

int main() {
    const char *so_path = getenv("REV_PLUGIN_SO");
    if (!so_path || !*so_path) {
        std::fprintf(stderr, "FAIL: REV_PLUGIN_SO not set\n");
        return 1;
    }

    // 1. dlopen the packaged plugin
    void *handle = dlopen(so_path, RTLD_NOW);
    if (!handle) {
        std::fprintf(stderr, "FAIL: dlopen(%s): %s\n", so_path, dlerror());
        return 1;
    }

    // 2. resolve ladspa_descriptor and inspect the descriptors
    void *sym = dlsym(handle, "ladspa_descriptor");
    if (!sym) {
        std::fprintf(stderr, "FAIL: ladspa_descriptor not exported: %s\n",
                     dlerror());
        return 1;
    }
    auto descriptor = reinterpret_cast<ladspa_descriptor_fn>(sym);

    unsigned long count = 0;
    unsigned long ports_total = 0;
    unsigned long ids[64] = {0};
    while (true) {
        const LADSPA_Descriptor *d = descriptor(count);
        if (!d) break;
        if (count < 64) ids[count] = d->UniqueID;
        if (!d->Label || !d->Name || !d->Maker) {
            std::fprintf(stderr, "FAIL: plugin %lu missing metadata\n", count);
            return 1;
        }
        ports_total += d->PortCount;
        count++;
    }
    if (count == 0) {
        std::fprintf(stderr, "FAIL: no LADSPA descriptors found\n");
        return 1;
    }
    for (unsigned long i = 0; i < count && i < 64; i++) {
        for (unsigned long j = i + 1; j < count && j < 64; j++) {
            if (ids[i] != 0 && ids[i] == ids[j]) {
                std::fprintf(stderr, "FAIL: duplicate UniqueID %lu\n", ids[i]);
                return 1;
            }
        }
    }
    std::printf("INFO: %lu LADSPA plugins, %lu ports total\n", count,
                ports_total);

    // 3. instantiate + run + cleanup lifecycle on a real buffer
    const LADSPA_Descriptor *d = descriptor(0);
    LADSPA_Handle h = d->instantiate(d, 48000);
    if (!h) {
        std::fprintf(stderr, "FAIL: instantiate failed\n");
        return 1;
    }

    const unsigned long sample_rate = 48000;
    const unsigned long nframes = 480;
    float in_l[nframes], in_r[nframes], out_l[nframes], out_r[nframes];
    for (unsigned long i = 0; i < nframes; i++) {
        in_l[i] = 0.25f * std::sin(2.0f * 3.14159265f * 440.0f * i / 48000.0f);
        in_r[i] = 0.25f * std::sin(2.0f * 3.14159265f * 550.0f * i / 48000.0f);
        out_l[i] = 0.0f;
        out_r[i] = 0.0f;
    }

    // Wire ports by descriptor: audio in/out and controls (0.0f defaults).
    // Stereo convention: first input port -> in_l, last input -> in_r,
    // first output -> out_l, last output -> out_r.
    float zero_ctl = 0.0f;
    unsigned long audio_in_seen = 0, audio_out_seen = 0;
    for (unsigned long p = 0; p < d->PortCount; p++) {
        LADSPA_PortDescriptor pd = d->PortDescriptors[p];
        if (pd & LADSPA_PORT_AUDIO) {
            if (pd & LADSPA_PORT_OUTPUT) {
                audio_out_seen++;
                d->connect_port(h, p, audio_out_seen == 1 ? out_l : out_r);
            } else {
                audio_in_seen++;
                d->connect_port(h, p, audio_in_seen == 1 ? in_l : in_r);
            }
        } else if (pd & LADSPA_PORT_CONTROL) {
            d->connect_port(h, p, &zero_ctl);
        }
    }

    if (d->activate) d->activate(h);
    d->run(h, nframes);
    if (d->deactivate) d->deactivate(h);
    d->cleanup(h);

    // reverb output must be non-silent (plugin actually processed audio)
    double energy = 0.0;
    for (unsigned long i = 0; i < nframes; i++) {
        energy += out_l[i] * out_l[i] + out_r[i] * out_r[i];
    }
    if (!(energy > 1e-9)) {
        std::fprintf(stderr,
                     "FAIL: plugin produced silence (energy=%g)\n", energy);
        return 1;
    }
    std::printf("INFO: run OK, output energy=%g\n", energy);

    dlclose(handle);
    std::printf("PASS: rev plugin consumer test\n");
    return 0;
}
