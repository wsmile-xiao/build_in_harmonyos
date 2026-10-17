/* sems-gsm consumer test — exercises the tested package itself (R34/R52).
 *
 * sems-gsm is an *application* package: its deliverables are the SEMS
 * plug-ins in lib/sems/plug-in/ and the sbin/ tools.  A test that only
 * calls libgsm's codec API would pass even if this package were empty, so
 * this consumer drives the package's own artefacts:
 *
 *   1. package layout   : sbin/sems and lib/sems/plug-in/gsm.so must exist
 *   2. plug-in loading  : dlopen(gsm.so, RTLD_NOW|RTLD_GLOBAL) — the plug-in
 *                         imports SEMS core symbols (log_level,
 *                         log_level2str, log_stderr, run_log_hooks); the
 *                         test binary exports them (--export-dynamic), the
 *                         same way sbin/sems does at runtime, so a missing
 *                         or renamed symbol inside the package fails here
 *   3. plug-in ABI      : dlsym("amci_exports"), the export struct the SEMS
 *                         loader looks up (48 bytes, core/plug-in/gsm/gsm.c)
 *   4. codec round trip : the package's own gsm_* symbols are resolved out
 *                         of the loaded plug-in and run on real data
 *
 * The package folder is passed in by test_package/conanfile.py through the
 * SEMS_PACKAGE_FOLDER environment variable.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

/* --- SEMS core symbols the plug-in relocates against (core/log.h) ------- */
int log_level = 0;
int log_stderr = 0;
const char *log_level2str[] = {
    "ERROR", "WARNING", "INFO", "DEBUG",
    "_DEBUG1", "_DEBUG2", "_DEBUG3", "_DEBUG4"
};
void run_log_hooks(int level, int pid, int tid, const char *func,
                   const char *file, int line, char *msg) {
    (void)level; (void)pid; (void)tid; (void)func;
    (void)file; (void)line; (void)msg;
}

/* --- libgsm codec API carried by the plug-in --------------------------- */
typedef void *gsm;
typedef short gsm_signal;
typedef unsigned char gsm_byte;
typedef gsm (*gsm_create_fn)(void);
typedef void (*gsm_destroy_fn)(gsm);
typedef void (*gsm_encode_fn)(gsm, gsm_signal *, gsm_byte *);
typedef int (*gsm_decode_fn)(gsm, gsm_byte *, gsm_signal *);

static int checks = 0;
static int failures = 0;

#define CHECK(cond, ...)                                                       \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failures++;                                                        \
            fprintf(stderr, "FAIL: " __VA_ARGS__);                             \
            fprintf(stderr, "\n");                                             \
        }                                                                      \
    } while (0)

static int is_regular_nonempty(const char *path, long *size) {
    struct stat st;
    if (stat(path, &st) != 0 || !S_ISREG(st.st_mode))
        return 0;
    if (size)
        *size = (long)st.st_size;
    return 1;
}

static int count_shared_objects(const char *dir) {
    DIR *d = opendir(dir);
    struct dirent *e;
    int n = 0;
    if (!d)
        return -1;
    while ((e = readdir(d)) != NULL) {
        size_t len = strlen(e->d_name);
        if (len > 3 && strcmp(e->d_name + len - 3, ".so") == 0)
            n++;
    }
    closedir(d);
    return n;
}

int main(void) {
    const char *pkg = getenv("SEMS_PACKAGE_FOLDER");
    CHECK(pkg && pkg[0], "SEMS_PACKAGE_FOLDER is not set by test_package");
    if (!pkg || !pkg[0])
        return 1;

    char sems_bin[4096], plugin[4096], plugindir[4096];
    snprintf(sems_bin, sizeof sems_bin, "%s/sbin/sems", pkg);
    snprintf(plugindir, sizeof plugindir, "%s/lib/sems/plug-in", pkg);
    snprintf(plugin, sizeof plugin, "%s/lib/sems/plug-in/gsm.so", pkg);

    long size = 0;
    CHECK(is_regular_nonempty(sems_bin, &size) && size > 0,
          "sbin/sems missing or empty in package (%s)", sems_bin);
    CHECK(is_regular_nonempty(plugin, &size) && size > 0,
          "sems-gsm plug-in missing or empty in package (%s)", plugin);
    int nplugins = count_shared_objects(plugindir);
    CHECK(nplugins >= 3, "expected >=3 plug-ins in %s, found %d",
          plugindir, nplugins);

    /* Load the package's plug-in exactly as the SEMS loader does. */
    void *h = dlopen(plugin, RTLD_NOW | RTLD_GLOBAL);
    CHECK(h != NULL, "dlopen(%s) failed: %s", plugin, dlerror());
    if (!h)
        goto report;

    void *entry = dlsym(h, "amci_exports");
    CHECK(entry != NULL, "plug-in ABI entry amci_exports not found: %s",
          dlerror());

    const char *syms[] = {"gsm_create", "gsm_encode", "gsm_decode",
                          "gsm_destroy"};
    void *addr[4];
    for (size_t i = 0; i < sizeof syms / sizeof syms[0]; i++) {
        addr[i] = dlsym(h, syms[i]);
        CHECK(addr[i] != NULL, "codec symbol %s not exported by plug-in",
              syms[i]);
    }
    /* gsm_option is not part of the subset the plug-in exports (SEMS builds
     * the codec from the libgsm sources it needs) — report, do not fail. */
    printf("note: gsm_option %s by the plug-in\n",
           dlsym(h, "gsm_option") ? "exported" : "not exported");

    if (!addr[0] || !addr[1] || !addr[2] || !addr[3]) {
        dlclose(h);
        goto report;
    }

    /* Real codec round trip through the package's own code. */
    gsm_create_fn create = (gsm_create_fn)addr[0];
    gsm_encode_fn encode = (gsm_encode_fn)addr[1];
    gsm_decode_fn decode = (gsm_decode_fn)addr[2];
    gsm_destroy_fn destroy = (gsm_destroy_fn)addr[3];

    gsm codec = create();
    CHECK(codec != NULL, "gsm_create() from the plug-in returned NULL");
    if (codec) {
        gsm_signal pcm[160], out[160];
        gsm_byte frame[33];
        /* GSM 06.10 is a 13-bit codec: keep input inside +-8191 */
        for (int i = 0; i < 160; i++)
            pcm[i] = (gsm_signal)((i % 40 - 20) * 200);
        encode(codec, pcm, frame);
        CHECK(decode(codec, frame, out) == 0, "gsm_decode() failed");
        int max_err = 0;
        for (int i = 0; i < 160; i++) {
            int err = out[i] - pcm[i];
            if (err < 0) err = -err;
            if (err > max_err) max_err = err;
        }
        CHECK(max_err <= 2048, "roundtrip error too large: max_err=%d",
              max_err);
        printf("codec round trip through package plug-in: max_err=%d\n",
               max_err);
        destroy(codec);
    }
    CHECK(dlclose(h) == 0, "dlclose failed: %s", dlerror());

report:
    printf("%s: sems-gsm package consumer checks: %d/%d passed\n",
           failures ? "FAIL" : "PASS", checks - failures, checks);
    return failures ? 1 : 0;
}
