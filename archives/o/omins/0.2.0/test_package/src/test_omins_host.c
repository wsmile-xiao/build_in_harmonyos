#include <dlfcn.h>
#include <ladspa.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#define FRAME_COUNT 64UL
#define EXPECTED_MODULES 18UL
#define EXPECTED_DESCRIPTORS 28UL

typedef const LADSPA_Descriptor *(*descriptor_function)(unsigned long);

static const char *const modules[EXPECTED_MODULES] = {
    "adenv.so",                "adenv_lvl.so",
    "comparison_4440.so",      "dahdsr_fexp.so",
    "dahdsr_hexp.so",          "fast_crossfade_4410.so",
    "formant_filter_4300.so",  "hz_voct_4200.so",
    "masher_4310.so",          "multiplexer_4420.so",
    "power_4400.so",           "prob_switch_2667.so",
    "range_trans_4210.so",     "sample_and_hold_4430.so",
    "signal_abs_2669.so",      "slew_limiter_2743.so",
    "slide_2741.so",           "waveguide_mesh_2670.so",
};

static float interpolate_default(const LADSPA_PortRangeHint *hint,
                                 float linear_weight) {
    const LADSPA_PortRangeHintDescriptor flags = hint->HintDescriptor;
    const float lower = LADSPA_IS_HINT_BOUNDED_BELOW(flags)
                            ? hint->LowerBound
                            : 0.0f;
    const float upper = LADSPA_IS_HINT_BOUNDED_ABOVE(flags)
                            ? hint->UpperBound
                            : 1.0f;
    if (LADSPA_IS_HINT_LOGARITHMIC(flags) && lower > 0.0f && upper > 0.0f) {
        return expf(logf(lower) * (1.0f - linear_weight) +
                    logf(upper) * linear_weight);
    }
    return lower * (1.0f - linear_weight) + upper * linear_weight;
}

static float control_value(const LADSPA_PortRangeHint *hint) {
    const LADSPA_PortRangeHintDescriptor flags = hint->HintDescriptor;
    float value;

    if (LADSPA_IS_HINT_DEFAULT_MINIMUM(flags)) {
        value = hint->LowerBound;
    } else if (LADSPA_IS_HINT_DEFAULT_LOW(flags)) {
        value = interpolate_default(hint, 0.25f);
    } else if (LADSPA_IS_HINT_DEFAULT_MIDDLE(flags)) {
        value = interpolate_default(hint, 0.5f);
    } else if (LADSPA_IS_HINT_DEFAULT_HIGH(flags)) {
        value = interpolate_default(hint, 0.75f);
    } else if (LADSPA_IS_HINT_DEFAULT_MAXIMUM(flags)) {
        value = hint->UpperBound;
    } else if (LADSPA_IS_HINT_DEFAULT_0(flags)) {
        value = 0.0f;
    } else if (LADSPA_IS_HINT_DEFAULT_1(flags)) {
        value = 1.0f;
    } else if (LADSPA_IS_HINT_DEFAULT_100(flags)) {
        value = 100.0f;
    } else if (LADSPA_IS_HINT_DEFAULT_440(flags)) {
        value = 440.0f;
    } else {
        value = interpolate_default(hint, 0.5f);
    }

    if (LADSPA_IS_HINT_SAMPLE_RATE(flags)) {
        value *= 48000.0f;
    }
    if (LADSPA_IS_HINT_TOGGLED(flags)) {
        value = value >= 0.5f ? 1.0f : 0.0f;
    } else if (LADSPA_IS_HINT_INTEGER(flags)) {
        value = roundf(value);
    }
    return value;
}

static int exercise_descriptor(const char *module,
                               const LADSPA_Descriptor *descriptor) {
    LADSPA_Handle instance = NULL;
    LADSPA_Data **buffers = NULL;
    unsigned long port;
    int activated = 0;
    int result = 1;

    if (descriptor->UniqueID == 0 || descriptor->Label == NULL ||
        descriptor->Name == NULL || descriptor->PortDescriptors == NULL ||
        descriptor->PortRangeHints == NULL || descriptor->instantiate == NULL ||
        descriptor->connect_port == NULL || descriptor->run == NULL ||
        descriptor->cleanup == NULL) {
        fprintf(stderr, "FAIL metadata: %s\n", module);
        return 0;
    }
    instance = descriptor->instantiate(descriptor, 48000UL);
    if (instance == NULL) {
        fprintf(stderr, "FAIL instantiate: %s:%s\n", module,
                descriptor->Label);
        return 0;
    }
    buffers = calloc(descriptor->PortCount, sizeof(*buffers));
    if (buffers == NULL) {
        fprintf(stderr, "FAIL allocate port table: %s:%s\n", module,
                descriptor->Label);
        goto cleanup;
    }

    for (port = 0; port < descriptor->PortCount; ++port) {
        unsigned long frame;
        buffers[port] = calloc(FRAME_COUNT, sizeof(**buffers));
        if (buffers[port] == NULL) {
            fprintf(stderr, "FAIL allocate port %lu: %s:%s\n", port,
                    module, descriptor->Label);
            goto cleanup;
        }
        if (LADSPA_IS_PORT_INPUT(descriptor->PortDescriptors[port])) {
            if (LADSPA_IS_PORT_CONTROL(descriptor->PortDescriptors[port])) {
                buffers[port][0] = control_value(&descriptor->PortRangeHints[port]);
            } else {
                for (frame = 0; frame < FRAME_COUNT; ++frame) {
                    if (strcmp(descriptor->Label, "hz_voct_ar") == 0) {
                        /* Frequency-to-voltage conversion requires Hz > 0. */
                        buffers[port][frame] = 440.0f;
                    } else if (strcmp(descriptor->Label, "power") == 0) {
                        /* Fractional powers require a non-negative base. */
                        buffers[port][frame] = 0.125f;
                    } else if (strcmp(descriptor->Label,
                                      "range_trans_ar") == 0 && port < 4UL) {
                        /* Use distinct, ordered source and destination ranges. */
                        static const float range_limits[] = {
                            0.0f, 1.0f, -1.0f, 1.0f,
                        };
                        buffers[port][frame] = range_limits[port];
                    } else {
                        buffers[port][frame] =
                            ((frame / 8UL) % 2UL == 0UL) ? 0.125f : -0.125f;
                    }
                }
            }
        }
        descriptor->connect_port(instance, port, buffers[port]);
    }

    if (descriptor->activate != NULL) {
        descriptor->activate(instance);
        activated = 1;
    }
    descriptor->run(instance, FRAME_COUNT);
    for (port = 0; port < descriptor->PortCount; ++port) {
        unsigned long frame;
        if (!LADSPA_IS_PORT_OUTPUT(descriptor->PortDescriptors[port])) {
            continue;
        }
        for (frame = 0; frame < FRAME_COUNT; ++frame) {
            if (!isfinite(buffers[port][frame])) {
                fprintf(stderr, "FAIL non-finite output: %s:%s port %lu\n",
                        module, descriptor->Label, port);
                goto cleanup;
            }
        }
    }
    result = 0;

cleanup:
    if (activated && descriptor->deactivate != NULL) {
        descriptor->deactivate(instance);
    }
    if (buffers != NULL) {
        for (port = 0; port < descriptor->PortCount; ++port) {
            free(buffers[port]);
        }
        free(buffers);
    }
    descriptor->cleanup(instance);
    if (result == 0) {
        printf("PASS %s:%s (ID %lu, %lu ports)\n", module,
               descriptor->Label, descriptor->UniqueID, descriptor->PortCount);
    }
    return result == 0;
}

int main(int argc, char **argv) {
    struct utsname system_info;
    unsigned long module_index;
    unsigned long descriptor_total = 0;

    setvbuf(stdout, NULL, _IONBF, 0);

    if (argc != 2) {
        fprintf(stderr, "usage: %s <ladspa-plugin-directory>\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (sizeof(modules) / sizeof(modules[0]) != EXPECTED_MODULES) {
        fprintf(stderr, "FAIL internal module inventory\n");
        return EXIT_FAILURE;
    }
    if (uname(&system_info) != 0 ||
        (strcmp(system_info.machine, "aarch64") != 0 &&
         strcmp(system_info.machine, "arm64") != 0)) {
        fprintf(stderr, "FAIL expected HarmonyOS aarch64 runtime\n");
        return EXIT_FAILURE;
    }
    printf("HarmonyOS runtime: %s %s %s\n", system_info.sysname,
           system_info.release, system_info.machine);

    for (module_index = 0; module_index < EXPECTED_MODULES; ++module_index) {
        char path[4096];
        void *library;
        descriptor_function ladspa_descriptor;
        unsigned long descriptor_index;

        if (snprintf(path, sizeof(path), "%s/%s", argv[1],
                     modules[module_index]) >= (int)sizeof(path)) {
            fprintf(stderr, "FAIL plugin path too long\n");
            return EXIT_FAILURE;
        }
        printf("LOAD %s\n", modules[module_index]);
        library = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (library == NULL) {
            fprintf(stderr, "FAIL dlopen %s: %s\n", path, dlerror());
            return EXIT_FAILURE;
        }
        *(void **)(&ladspa_descriptor) = dlsym(library, "ladspa_descriptor");
        if (ladspa_descriptor == NULL) {
            fprintf(stderr, "FAIL dlsym %s: %s\n", path, dlerror());
            dlclose(library);
            return EXIT_FAILURE;
        }
        for (descriptor_index = 0;; ++descriptor_index) {
            const LADSPA_Descriptor *descriptor =
                ladspa_descriptor(descriptor_index);
            if (descriptor == NULL) {
                break;
            }
            printf("TEST %s descriptor %lu\n", modules[module_index],
                   descriptor_index);
            if (!exercise_descriptor(modules[module_index], descriptor)) {
                dlclose(library);
                return EXIT_FAILURE;
            }
            ++descriptor_total;
        }
        if (descriptor_index == 0) {
            fprintf(stderr, "FAIL no descriptors in %s\n", path);
            dlclose(library);
            return EXIT_FAILURE;
        }
        dlclose(library);
    }

    if (descriptor_total != EXPECTED_DESCRIPTORS) {
        fprintf(stderr, "FAIL expected %lu descriptors, found %lu\n",
                EXPECTED_DESCRIPTORS, descriptor_total);
        return EXIT_FAILURE;
    }
    printf("PASS: %lu modules and %lu LADSPA descriptors exercised\n",
           EXPECTED_MODULES, descriptor_total);
    return EXIT_SUCCESS;
}
