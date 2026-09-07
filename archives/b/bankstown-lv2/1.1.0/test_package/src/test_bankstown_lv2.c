/*
 * test_bankstown_lv2.c — real LV2 C API consumer for bankstown-lv2 1.1.0.
 *
 * dlopen()s the packaged bankstown.so LV2 bundle binary, resolves the LV2
 * version 1.18 discovery entry point `lv2_descriptor(uint32_t)`, and drives
 * the plugin through the standard LV2 lifecycle:
 *
 *   lv2_descriptor(0)            → LV2_Descriptor* (URI must match
 *                                   https://chadmed.au/bankstown)
 *   descriptor->instantiate(...) → LV2_Handle (fsample_rate 48000)
 *   descriptor->connect_port(...) → 12 ports (in_l/in_r/out_l/out_r +
 *                                   bypass/amt/floor/ceil/final_hp/
 *                                   sat_second/sat_third/blend)
 *   descriptor->activate(...)
 *   descriptor->run(handle, n)   → bass-enhancement processing
 *   descriptor->deactivate(...)
 *   descriptor->cleanup(...)
 *
 * No upstream test harness exists, so this is the consumer-side real-API
 * verification (R34). Any step that fails prints FAIL and exits non-zero.
 */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* LV2 core structs (subset sufficient for driving the plugin, mirroring
 * the LV2 1.18 specification; layout matches lv2-sys bindings). */
typedef void *LV2_Handle;
typedef struct {
    const void *data;
} LV2_Feature;

/* The plugin URI, from manifest.ttl / bankstown.ttl. */
#define PLUGIN_URI "https://chadmed.au/bankstown"
/* Port layout from bankstown.ttl: 0-3 audio (in_l/in_r/out_l/out_r),
 * 4-11 control (bypass/amt/floor/ceil/final_hp/sat_second/sat_third/blend). */
#define N_PORTS 12
#define PORT_IN_L 0
#define PORT_IN_R 1
#define PORT_OUT_L 2
#define PORT_OUT_R 3

/* Forward declaration so the function-pointer typedefs can reference it;
 * the full struct is defined below. */
struct LV2_Descriptor;

typedef LV2_Handle (*instantiate_fn)(const struct LV2_Descriptor *descriptor,
                                     double sample_rate,
                                     const char *bundle_path,
                                     const LV2_Feature *const *features);
typedef void (*connect_port_fn)(LV2_Handle instance, uint32_t port,
                                void *data_location);
typedef void (*activate_fn)(LV2_Handle instance);
typedef void (*run_fn)(LV2_Handle instance, uint32_t sample_count);
typedef void (*deactivate_fn)(LV2_Handle instance);
typedef void (*cleanup_fn)(LV2_Handle instance);
typedef const void *(*extension_data_fn)(const char *uri);

struct LV2_Descriptor {
    const char *URI;
    instantiate_fn instantiate;
    connect_port_fn connect_port;
    activate_fn activate;
    run_fn run;
    deactivate_fn deactivate;
    cleanup_fn cleanup;
    extension_data_fn extension_data;
};

typedef const struct LV2_Descriptor *(*lv2_descriptor_fn)(uint32_t index);

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (cond) {                                                          \
            printf("PASS: %s\n", msg);                                       \
        } else {                                                             \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(int argc, char **argv) {
    char bundle_bin[4096];
    void *handle;
    lv2_descriptor_fn lv2_descriptor_sym;
    const struct LV2_Descriptor *desc;
    LV2_Handle instance;
    /* LV2 spec: features MUST NOT be NULL — pass an empty array. */
    const LV2_Feature *const features[] = { NULL };

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-bankstown.lv2-bundle>\n", argv[0]);
        return 2;
    }
    snprintf(bundle_bin, sizeof(bundle_bin), "%s/bankstown.so", argv[1]);

    /* 1. dlopen the plugin binary. */
    handle = dlopen(bundle_bin, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", bundle_bin, dlerror());
        return 1;
    }
    printf("PASS: dlopen(%s)\n", bundle_bin);

    /* 2. Resolve the LV2 discovery symbol. */
    *(void **)(&lv2_descriptor_sym) = dlsym(handle, "lv2_descriptor");
    if (!lv2_descriptor_sym) {
        fprintf(stderr, "FAIL: dlsym lv2_descriptor: %s\n", dlerror());
        return 1;
    }
    printf("PASS: dlsym lv2_descriptor\n");

    /* 3. Get descriptor[0] and verify the URI. */
    desc = lv2_descriptor_sym(0);
    CHECK(desc != NULL, "lv2_descriptor(0) non-NULL");
    if (!desc) return 1;
    CHECK(desc->URI != NULL, "descriptor->URI non-NULL");
    if (desc->URI) {
        printf("INFO: plugin URI = %s\n", desc->URI);
        CHECK(strcmp(desc->URI, PLUGIN_URI) == 0, "plugin URI matches https://chadmed.au/bankstown");
    }
    CHECK(desc->instantiate != NULL, "descriptor->instantiate present");
    CHECK(desc->connect_port != NULL, "descriptor->connect_port present");
    CHECK(desc->activate != NULL, "descriptor->activate present");
    CHECK(desc->run != NULL, "descriptor->run present");
    CHECK(desc->deactivate != NULL, "descriptor->deactivate present");
    CHECK(desc->cleanup != NULL, "descriptor->cleanup present");

    /* 4. Instantiate at 48000 Hz. */
    instance = desc->instantiate(desc, 48000.0, argv[1], features);
    CHECK(instance != NULL, "instantiate(48000 Hz) non-NULL");
    if (!instance) return 1;

    /* 5. Connect all 12 ports. */
    {
        float in_l[64], in_r[64], out_l[64], out_r[64];
        float bypass = 0.0f, amt = 1.0f, floor = 20.0f, ceil = 200.0f;
        float final_hp = 200.0f, sat_second = 1.0f, sat_third = 1.0f, blend = 0.5f;
        uint32_t i;
        int output_changed;
        static const int n = 64;

        for (i = 0; i < n; i++) {
            /* 110 Hz sine ≈ borderline piano fundamental — the band the
             * plugin enhances. */
            in_l[i] = 0.25f * (float)__builtin_sinf(2.0f * 3.14159265f * 110.0f * (float)i / 48000.0f);
            in_r[i] = in_l[i];
            out_l[i] = 0.0f;
            out_r[i] = 0.0f;
        }

        desc->connect_port(instance, PORT_IN_L, in_l);
        desc->connect_port(instance, PORT_IN_R, in_r);
        desc->connect_port(instance, PORT_OUT_L, out_l);
        desc->connect_port(instance, PORT_OUT_R, out_r);
        desc->connect_port(instance, 4, &bypass);
        desc->connect_port(instance, 5, &amt);
        desc->connect_port(instance, 6, &floor);
        desc->connect_port(instance, 7, &ceil);
        desc->connect_port(instance, 8, &final_hp);
        desc->connect_port(instance, 9, &sat_second);
        desc->connect_port(instance, 10, &sat_third);
        desc->connect_port(instance, 11, &blend);
        printf("PASS: connected 12 ports\n");

        desc->activate(instance);
        desc->run(instance, n);
        desc->deactivate(instance);

        /* Output must have been written: the processed signal differs from
         * the all-zeros output we connected. */
        output_changed = 0;
        for (i = 0; i < n; i++) {
            if (out_l[i] != 0.0f || out_r[i] != 0.0f) {
                output_changed = 1;
                break;
            }
        }
        CHECK(output_changed, "run() wrote non-zero output (processing happened)");

        /* Bypass mode: output should equal the clamped input (scaled 1.0).
         * With bypass=1 the run() loop copies in*1.0 to out. */
        bypass = 1.0f;
        {
            float by_out_l[64], by_out_r[64];
            for (i = 0; i < n; i++) {
                by_out_l[i] = 0.0f;
                by_out_r[i] = 0.0f;
            }
            desc->connect_port(instance, PORT_OUT_L, by_out_l);
            desc->connect_port(instance, PORT_OUT_R, by_out_r);
            desc->activate(instance);
            desc->run(instance, n);
            desc->deactivate(instance);
            {
                int bypass_ok = 1;
                for (i = 0; i < n; i++) {
                    if (by_out_l[i] != in_l[i] || by_out_r[i] != in_r[i]) {
                        bypass_ok = 0;
                        break;
                    }
                }
                CHECK(bypass_ok, "bypass mode passes input through unchanged");
            }
        }
    }

    /* 6. Cleanup. */
    desc->cleanup(instance);
    printf("PASS: cleanup\n");

    dlclose(handle);
    printf("bankstown-lv2 test: %s (%d failure%s)\n",
           failures == 0 ? "PASS" : "FAIL", failures, failures == 1 ? "" : "s");
    return failures == 0 ? 0 : 1;
}