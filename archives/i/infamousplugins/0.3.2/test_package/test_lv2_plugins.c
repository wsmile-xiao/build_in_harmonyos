/* test_lv2_plugins.c — consumer test for the infamousPlugins LV2 bundles.
 *
 * For every installed bundle (lib/lv2/<plug>.lv2/) the test
 *   1. reads the port map from the bundle's own .ttl file
 *      (lv2:index + lv2:InputPort/lv2:OutputPort + AudioPort/ControlPort/
 *       CVPort/AtomPort + lv2:default), so nothing is hard-coded;
 *   2. dlopen()s <plug>.so with RTLD_NOW;
 *   3. resolves the lv2_descriptor() entry point and checks every URI;
 *   4. drives a full LV2 life cycle: instantiate -> connect_port (every port,
 *      audio inputs fed with a 440 Hz sine, control/CV inputs at their declared
 *      lv2:default) -> activate -> run (8 blocks of 256 frames) -> deactivate
 *      -> cleanup;
 *   5. asserts every audio output stays finite (no NaN / Inf).
 *
 * R34: the package is really executed here — the DSP code of every bundle runs
 * with real audio, this is not a print-only stub.
 *
 * Usage: test_lv2_plugins <lv2-bundle-root>
 * Prints one "TEST_RESULT={...}" JSON line for the driver to collect.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lv2/core/lv2.h>
#include <lv2/urid/urid.h>

#define MAX_PORT_INDEX 256
#define MAX_BUNDLES 64
#define PORT_BUFFER_BYTES 4096
#define BLOCK_SAMPLES 256
#define BLOCK_RUNS 8

static int g_checks;
static int g_failed;

static void check(int cond, const char *what, const char *detail)
{
    g_checks++;
    if (cond) {
        printf("  ok   %s%s%s\n", what, detail ? ": " : "", detail ? detail : "");
    } else {
        g_failed++;
        printf("  FAIL %s%s%s\n", what, detail ? ": " : "", detail ? detail : "");
    }
}

/* ── minimal LV2_URID map/unmap so plug-ins requesting it can instantiate ── */

typedef struct {
    char *uri;
    uint32_t id;
} urid_entry;

static urid_entry g_urids[MAX_PORT_INDEX];
static uint32_t g_urid_count;

static LV2_URID urid_map_cb(LV2_URID_Map_Handle handle, const char *uri)
{
    (void)handle;
    for (uint32_t i = 0; i < g_urid_count; i++)
        if (strcmp(g_urids[i].uri, uri) == 0)
            return g_urids[i].id;
    if (g_urid_count >= MAX_PORT_INDEX)
        return 0;
    char *copy = strdup(uri);
    if (!copy)
        return 0;
    g_urids[g_urid_count].uri = copy;
    g_urids[g_urid_count].id = g_urid_count + 1; /* 0 stays "invalid" */
    return g_urids[g_urid_count++].id;
}

static const char *urid_unmap_cb(LV2_URID_Unmap_Handle handle, LV2_URID urid)
{
    (void)handle;
    for (uint32_t i = 0; i < g_urid_count; i++)
        if (g_urids[i].id == urid)
            return g_urids[i].uri;
    return NULL;
}

static LV2_URID_Map g_urid_map = {NULL, urid_map_cb};
static LV2_URID_Unmap g_urid_unmap = {NULL, urid_unmap_cb};
static const LV2_Feature g_feature_map = {LV2_URID__map, &g_urid_map};
static const LV2_Feature g_feature_unmap = {LV2_URID__unmap, &g_urid_unmap};
static const LV2_Feature *const g_features[] = {&g_feature_map, &g_feature_unmap, NULL};

/* ── port map extracted from the bundle's .ttl ── */

typedef struct {
    int max_index;
    int has_index[MAX_PORT_INDEX];
    int audio_in[MAX_PORT_INDEX];
    int audio_out[MAX_PORT_INDEX];
    int control_in[MAX_PORT_INDEX];
    float control_default[MAX_PORT_INDEX];
} port_map;

static char *slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    long size = ftell(f);
    if (size < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    char *buf = malloc((size_t)size + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t got = fread(buf, 1, (size_t)size, f);
    buf[got] = '\0';
    fclose(f);
    return buf;
}

static void port_element(const char *open, const char *close, port_map *map)
{
    size_t len = (size_t)(close - open) + 1;
    char block[4096];
    if (len >= sizeof(block))
        len = sizeof(block) - 1;
    memcpy(block, open, len);
    block[len] = '\0';

    char *index_tok = strstr(block, "lv2:index");
    if (!index_tok)
        return;
    int index = atoi(index_tok + strlen("lv2:index"));
    if (index < 0 || index >= MAX_PORT_INDEX)
        return;

    map->has_index[index] = 1;
    if (index > map->max_index)
        map->max_index = index;

    int is_input = strstr(block, "InputPort") != NULL;
    int is_output = strstr(block, "OutputPort") != NULL;
    int is_audio = strstr(block, "AudioPort") != NULL;
    int is_atom = strstr(block, "AtomPort") != NULL;
    int is_control = strstr(block, "ControlPort") != NULL;
    int is_cv = strstr(block, "CVPort") != NULL;

    if (is_input && is_audio && !is_atom)
        map->audio_in[index] = 1;
    if (is_output && is_audio && !is_atom)
        map->audio_out[index] = 1;
    if (is_input && !is_audio && !is_atom && (is_control || is_cv))
        map->control_in[index] = 1;

    if (map->control_in[index]) {
        char *default_tok = strstr(block, "lv2:default");
        if (default_tok) {
            char *end = NULL;
            float value = strtof(default_tok + strlen("lv2:default"), &end);
            if (end && end != default_tok + strlen("lv2:default"))
                map->control_default[index] = value;
        }
    }
}

/* LV2 writes a port list as `lv2:port [ ... ] ;` or, for several ports,
 * `lv2:port [ ... ], [ ... ], [ ... ] ;` — every element carries its own
 * lv2:index (these bundles declare the index explicitly). */
static void scan_ttl_ports(const char *ttl_path, port_map *map)
{
    memset(map, 0, sizeof(*map));
    map->max_index = -1;

    char *buf = slurp(ttl_path);
    if (!buf)
        return;

    char *cursor = buf;
    while ((cursor = strstr(cursor, "lv2:port")) != NULL) {
        char *p = cursor + strlen("lv2:port");
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
            p++;
        if (*p != '[') { /* lv2:portProperty and friends */
            cursor = p;
            continue;
        }

        for (;;) {
            char *open = p;
            /* an element may contain nested lists (lv2:scalePoints [ ... ]),
             * so match the closing bracket by depth */
            int depth = 0;
            char *close = NULL;
            for (char *q = open; *q; q++) {
                if (*q == '[')
                    depth++;
                else if (*q == ']' && --depth == 0) {
                    close = q;
                    break;
                }
            }
            if (!close) {
                cursor = open + 1;
                break;
            }
            port_element(open, close, map);

            p = close + 1;
            while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
                p++;
            if (*p != ',') { /* end of this port list */
                cursor = close + 1;
                break;
            }
            p++;
            while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
                p++;
            if (*p != '[') {
                cursor = p;
                break;
            }
        }
    }
    free(buf);
}

/* ── one full LV2 life cycle ── */

static int run_plugin(const char *bundle_dir, const LV2_Descriptor *desc,
                      const port_map *map)
{
    void *buffers[MAX_PORT_INDEX];
    int ok = 1;

    for (int i = 0; i < MAX_PORT_INDEX; i++)
        buffers[i] = NULL;

    LV2_Handle instance = desc->instantiate(desc, 48000.0, bundle_dir, g_features);
    if (!instance)
        return 0;

    for (int i = 0; i <= map->max_index; i++) {
        buffers[i] = calloc(1, PORT_BUFFER_BYTES);
        if (!buffers[i])
            ok = 0;
    }

    if (ok) {
        for (int i = 0; i <= map->max_index; i++) {
            if (map->audio_in[i]) {
                float *in = (float *)buffers[i];
                for (int s = 0; s < BLOCK_SAMPLES; s++)
                    in[s] = 0.5f * sinf(2.0f * (float)M_PI * 440.0f * (float)s / 48000.0f);
            } else if (map->control_in[i]) {
                *(float *)buffers[i] = map->control_default[i];
            }
            desc->connect_port(instance, (uint32_t)i, buffers[i]);
        }

        /* activate/deactivate are optional in LV2 — these bundles (e.g. casynth)
         * leave them NULL */
        if (desc->activate)
            desc->activate(instance);
        for (int run = 0; run < BLOCK_RUNS; run++)
            desc->run(instance, BLOCK_SAMPLES);
        if (desc->deactivate)
            desc->deactivate(instance);
    }

    if (ok) {
        for (int i = 0; i <= map->max_index; i++) {
            if (!map->audio_out[i])
                continue;
            const float *out = (const float *)buffers[i];
            for (int s = 0; s < BLOCK_SAMPLES; s++) {
                if (!isfinite(out[s])) {
                    printf("  info port %d sample %d = %f\n", i, s, (double)out[s]);
                    ok = 0;
                    break;
                }
            }
        }
    }

    if (desc->cleanup)
        desc->cleanup(instance);
    for (int i = 0; i <= map->max_index; i++)
        free(buffers[i]);
    return ok;
}

int main(int argc, char **argv)
{
    /* keep the log usable when the program dies in a plug-in */
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != 2) {
        fprintf(stderr, "usage: %s <lv2-bundle-root>\n", argv[0]);
        return 2;
    }
    const char *root = argv[1];

    char names[MAX_BUNDLES][256];
    int bundles = 0;

    DIR *dir = opendir(root);
    if (!dir) {
        fprintf(stderr, "FAIL: cannot open LV2 bundle root %s\n", root);
        return 2;
    }
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        size_t n = strlen(entry->d_name);
        if (n < 5 || strcmp(entry->d_name + n - 4, ".lv2") != 0)
            continue;
        if (bundles >= MAX_BUNDLES)
            break;
        snprintf(names[bundles++], 256, "%s", entry->d_name);
    }
    closedir(dir);

    check(bundles > 0, "bundle root contains at least one .lv2 bundle", root);
    printf("  info %d LV2 bundles found\n", bundles);

    for (int b = 0; b < bundles; b++) {
        char plug[256];
        snprintf(plug, sizeof(plug), "%s", names[b]);
        plug[strlen(plug) - 4] = '\0';

        char bundle_dir[1024];
        char so_path[1024];
        char ttl_path[1024];
        snprintf(bundle_dir, sizeof(bundle_dir), "%s/%s", root, names[b]);
        snprintf(so_path, sizeof(so_path), "%s/%s.so", bundle_dir, plug);
        snprintf(ttl_path, sizeof(ttl_path), "%s/%s.ttl", bundle_dir, plug);

        printf("--- %s\n", names[b]);

        port_map map;
        scan_ttl_ports(ttl_path, &map);
        char detail[1200];
        snprintf(detail, sizeof(detail), "%s (%d ports)", ttl_path, map.max_index + 1);
        check(map.max_index >= 0, "port map read from bundle .ttl", detail);

        void *handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            check(0, "dlopen(plugin, RTLD_NOW)", dlerror());
            continue;
        }
        check(1, "dlopen(plugin, RTLD_NOW)", so_path);

        const LV2_Descriptor *(*descriptor)(uint32_t) =
            (const LV2_Descriptor *(*)(uint32_t))dlsym(handle, "lv2_descriptor");
        if (!descriptor) {
            check(0, "lv2_descriptor() exported", dlerror());
            dlclose(handle);
            continue;
        }
        check(1, "lv2_descriptor() exported", plug);

        int descriptors = 0;
        for (uint32_t i = 0; i < 32; i++) {
            const LV2_Descriptor *desc = descriptor(i);
            if (!desc)
                break;
            descriptors++;

            snprintf(detail, sizeof(detail), "descriptor[%u]", i);
            check(desc->URI != NULL && desc->URI[0] != '\0',
                  "plug-in URI is set", desc->URI ? desc->URI : "()");

            snprintf(detail, sizeof(detail), "descriptor[%u] %s", i,
                     desc->URI ? desc->URI : "(no URI)");
            check(run_plugin(bundle_dir, desc, &map),
                  "instantiate/run/deactivate/cleanup with audio", detail);
        }
        check(descriptors > 0, "descriptor list is not empty", plug);
        dlclose(handle);
    }

    printf("TEST_RESULT={\"bundles\":%d,\"discovered\":%d,\"passed\":%d,\"failed\":%d}\n",
           bundles, g_checks, g_checks - g_failed, g_failed);
    printf("%s: %d/%d checks passed\n", g_failed ? "FAIL" : "PASS",
           g_checks - g_failed, g_checks);
    return g_failed ? 1 : 0;
}
