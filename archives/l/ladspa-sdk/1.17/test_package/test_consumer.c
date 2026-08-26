/* test_consumer.c
 *
 * Consumer test for ladspa-sdk. It exercises the two halves of the LADSPA ABI
 * the SDK guarantees:
 *
 *  1. The header is usable to AUTHOR a plugin: test_minplugin.so was built by
 *     the consumer against the installed ladspa.h.
 *  2. The header is usable to HOST a plugin: we dlopen() test_minplugin.so and
 *     the installed example amp.so, look up ladspa_descriptor(), and drive a
 *     full instantiate -> connect_port -> activate -> run -> cleanup cycle.
 *
 * argv[1] = path to the consumer-built test_minplugin.so
 * argv[2] = name used in error messages for the consumer plugin
 * argv[3] = the test_package source dir (unused, reserved)
 *
 * Exit code is the number of failed assertions (0 = all passed).
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "ladspa.h"

static int g_failed = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            g_failed++;                                                      \
        } else {                                                             \
            printf("ok: %s\n", msg);                                         \
        }                                                                    \
    } while (0)

/* Resolve ladspa_descriptor from a dlopen'd handle and count plugins. */
static const LADSPA_Descriptor *(*find_descriptor_fn(void *h))(
    unsigned long) {
    dlerror();
    const LADSPA_Descriptor *(*fn)(unsigned long) =
        (const LADSPA_Descriptor *(*)(unsigned long))
        dlsym(h, "ladspa_descriptor");
    if (!fn) {
        const char *err = dlerror();
        fprintf(stderr, "dlsym ladspa_descriptor: %s\n",
                err ? err : "(null)");
    }
    return fn;
}

/* Drive a complete host cycle over the first descriptor. */
static int run_one(const LADSPA_Descriptor *d, unsigned long sample_rate,
                   unsigned long block) {
    if (!d || d->PortCount == 0 || !d->PortDescriptors ||
        !d->instantiate || !d->connect_port || !d->run || !d->cleanup)
        return 0;

    LADSPA_Handle h = d->instantiate(d, sample_rate);
    if (!h)
        return 0;

    /* Buffers for every port. */
    LADSPA_Data *bufs =
        (LADSPA_Data *)calloc(d->PortCount, block * sizeof(LADSPA_Data));
    if (!bufs) {
        d->cleanup(h);
        return 0;
    }

    for (unsigned long p = 0; p < d->PortCount; p++)
        d->connect_port(h, p, bufs + p * block);

    if (d->activate)
        d->activate(h);

    /* Find an input audio port and seed it. */
    for (unsigned long p = 0; p < d->PortCount; p++) {
        if ((d->PortDescriptors[p] & LADSPA_PORT_AUDIO) &&
            (d->PortDescriptors[p] & LADSPA_PORT_INPUT)) {
            for (unsigned long i = 0; i < block; i++)
                bufs[p * block + i] =
                    (LADSPA_Data)((long)(i % 256) - 128L) / 128.0f;
            break;
        }
    }

    d->run(h, block);

    if (d->deactivate)
        d->deactivate(h);

    d->cleanup(h);
    free(bufs);
    return 1;
}

static int test_plugin(const char *path, const char *label_hint) {
    void *h = dlopen(path, RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen %s: %s\n", path, dlerror());
        return 1;
    }
    const LADSPA_Descriptor *(*fn)(unsigned long) = find_descriptor_fn(h);
    CHECK(fn != NULL, "ladspa_descriptor symbol present");

    /* Count plugins by scanning until NULL. */
    unsigned long count = 0;
    if (fn) {
        while (fn(count) != NULL) count++;
    }
    CHECK(count >= 1, "at least one plugin descriptor exported");

    const LADSPA_Descriptor *d = fn ? fn(0) : NULL;
    if (d) {
        char buf[128];
        snprintf(buf, sizeof(buf), "%s: UniqueID nonzero", label_hint);
        CHECK(d->UniqueID != 0, buf);
        snprintf(buf, sizeof(buf), "%s: Label non-null/non-empty", label_hint);
        CHECK(d->Label != NULL && d->Label[0] != '\0', buf);
        snprintf(buf, sizeof(buf), "%s: Name non-null", label_hint);
        CHECK(d->Name != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: Maker non-null", label_hint);
        CHECK(d->Maker != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: Copyright non-null", label_hint);
        CHECK(d->Copyright != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: PortCount >= 1", label_hint);
        CHECK(d->PortCount >= 1, buf);
        snprintf(buf, sizeof(buf), "%s: PortDescriptors non-null", label_hint);
        CHECK(d->PortDescriptors != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: PortNames non-null", label_hint);
        CHECK(d->PortNames != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: PortRangeHints non-null", label_hint);
        CHECK(d->PortRangeHints != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: instantiate fn present", label_hint);
        CHECK(d->instantiate != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: connect_port fn present", label_hint);
        CHECK(d->connect_port != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: run fn present", label_hint);
        CHECK(d->run != NULL, buf);
        snprintf(buf, sizeof(buf), "%s: cleanup fn present", label_hint);
        CHECK(d->cleanup != NULL, buf);
        /* run_adding and set_run_adding_gain must be both-NULL or both-set. */
        int ra_ok = (d->run_adding == NULL) == (d->set_run_adding_gain == NULL);
        snprintf(buf, sizeof(buf),
                 "%s: run_adding/set_run_adding_gain paired", label_hint);
        CHECK(ra_ok, buf);
        /* Drive a full host cycle. */
        snprintf(buf, sizeof(buf), "%s: full host cycle (run) ok", label_hint);
        CHECK(run_one(d, 48000UL, 256UL), buf);
    }
    dlclose(h);
    return g_failed;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <consumer_plugin.so> [name] [srcdir]\n",
                argv[0]);
        return 2;
    }
    const char *consumer_path = argv[1];
    const char *consumer_name = argc > 2 ? argv[2] : "consumer";

    int failures = test_plugin(consumer_path, consumer_name);

    /* Now exercise the installed example amp.so from the package, found via
     * LADSPA_PATH (set by package_info) or the package's lib/ladspa. */
    const char *pkg_lib = getenv("CONAN_LADSPA_LIB");
    char amp_path[4096];
    const char *amp = NULL;
    if (pkg_lib) {
        snprintf(amp_path, sizeof(amp_path), "%s/amp.so", pkg_lib);
        amp = amp_path;
    } else {
        /* fall back to LADSPA_PATH search */
        const char *lp = getenv("LADSPA_PATH");
        if (lp) {
            const char *p = lp, *e;
            while (*p) {
                e = strchr(p, ':');
                size_t len = e ? (size_t)(e - p) : strlen(p);
                snprintf(amp_path, sizeof(amp_path), "%.*s/amp.so", (int)len, p);
                if (access(amp_path, R_OK) == 0) { amp = amp_path; break; }
                if (!e) break;
                p = e + 1;
            }
        }
    }
    if (amp) {
        printf("found example plugin: %s\n", amp);
        int f2 = test_plugin(amp, "amp.so");
        if (f2 > failures) failures = f2;
    } else {
        fprintf(stderr, "note: amp.so not found (skipping example test)\n");
    }

    /* LADSPA_Data must be float (the ABI's base scalar type). */
    CHECK(sizeof(LADSPA_Data) == sizeof(float),
          "LADSPA_Data is float-sized (ABI scalar)");
    if (g_failed > failures)
        failures = g_failed;

    if (failures == 0)
        printf("\nALL LADSPA ABI assertions passed\n");
    else
        printf("\n%d assertion(s) FAILED\n", failures);
    return failures;
}
