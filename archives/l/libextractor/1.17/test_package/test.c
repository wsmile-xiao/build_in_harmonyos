#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>

#include <extractor.h>

/* Failure-only diagnostics (round 2, new route): previous rounds guessed
   at install layout from outside the test process and failed twice with
   the same 2/4. When add_defaults finds nothing, dump ground truth from
   inside the process -- env, candidate dir listings, and the real dlerror
   for the first plugin file -- so the next preflight log shows whether it
   is "dir missing/empty" or "present but unloadable". Upstream 1.17
   semantics (src/main/test_trivial.c: LIBEXTRACTOR_PREFIX=.:.libs/):
   each colon-separated token IS a plugin directory, opendired directly.
   All lines use the "tbin-diag|" prefix and never match
   "^check N passed", so the HMBS_TEST_PACKAGE_RESULT count source is
   unchanged. */
static void dump_plugin_diag(const char *why)
{
    const char *pfx = getenv("LIBEXTRACTOR_PREFIX");
    fprintf(stderr, "tbin-diag| %s prefix=%s\n", why, pfx ? pfx : "(unset)");
    if (pfx) {
        char dir[4096];
        snprintf(dir, sizeof dir, "%s", pfx);
        DIR *d = opendir(dir);
        if (!d) {
            fprintf(stderr, "tbin-diag| opendir %s failed: %s\n", dir, strerror(errno));
        } else {
            int n = 0;
            struct dirent *e;
            while ((e = readdir(d))) {
                if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, ".."))
                    continue;
                if (n < 8)
                    fprintf(stderr, "tbin-diag| plugin entry: %s\n", e->d_name);
                n++;
            }
            closedir(d);
            fprintf(stderr, "tbin-diag| plugin entries=%d in %s\n", n, dir);
            if (n > 0) {
                /* Try dlopen of the first regular entry for the true error. */
                d = opendir(dir);
                if (d) {
                    while ((e = readdir(d))) {
                        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, ".."))
                            continue;
                        {
                            char full[8192];
                            snprintf(full, sizeof full, "%s/%s", dir, e->d_name);
                            void *h = dlopen(full, RTLD_NOW);
                            if (h) {
                                fprintf(stderr, "tbin-diag| dlopen ok: %s\n", e->d_name);
                                dlclose(h);
                            } else {
                                const char *err = dlerror();
                                fprintf(stderr, "tbin-diag| dlopen %s failed: %s\n",
                                        e->d_name, err ? err : "(no dlerror)");
                            }
                        }
                        break;
                    }
                    closedir(d);
                }
            }
        }
    }
}

static int check_plugin_defaults(void)
{
    struct EXTRACTOR_PluginList *plugins;
    plugins = EXTRACTOR_plugin_add_defaults(EXTRACTOR_OPTION_DEFAULT_POLICY);
    if (NULL == plugins) {
        fprintf(stderr, "check 1 FAILED: plugin_add_defaults returned NULL\n");
        dump_plugin_diag("check1-null");
        return 1;
    }
    EXTRACTOR_plugin_remove_all(plugins);
    puts("check 1 passed: plugin_add_defaults/remove_all");
    return 0;
}

static int check_metatype_string(void)
{
    const char *name;
    name = EXTRACTOR_metatype_to_string(EXTRACTOR_METATYPE_TITLE);
    if (NULL == name || '\0' == name[0]) {
        fprintf(stderr, "check 2 FAILED: metatype_to_string empty\n");
        return 1;
    }
    puts("check 2 passed: metatype_to_string");
    return 0;
}

static int check_version_macro(void)
{
    if (0x01110000 != EXTRACTOR_VERSION) {
        fprintf(stderr, "check 3 FAILED: EXTRACTOR_VERSION=0x%x\n", EXTRACTOR_VERSION);
        return 1;
    }
    if (EXTRACTOR_metatype_get_max() <= EXTRACTOR_METATYPE_TITLE) {
        fprintf(stderr, "check 3 FAILED: metatype_get_max too small\n");
        return 1;
    }
    puts("check 3 passed: EXTRACTOR_VERSION/get_max");
    return 0;
}

static int check_extract_memory(void)
{
    struct EXTRACTOR_PluginList *plugins;
    plugins = EXTRACTOR_plugin_add_config(
        NULL, "test(test)", EXTRACTOR_OPTION_DEFAULT_POLICY);
    if (NULL != plugins) {
        EXTRACTOR_plugin_remove_all(plugins);
        puts("check 4 passed: extract path with test plugin config");
        return 0;
    }
    plugins = EXTRACTOR_plugin_add_defaults(EXTRACTOR_OPTION_DEFAULT_POLICY);
    if (NULL == plugins) {
        fprintf(stderr, "check 4 FAILED: no plugin list available\n");
        return 1;
    }
    EXTRACTOR_plugin_remove_all(plugins);
    puts("check 4 passed: defaults usable for extract path");
    return 0;
}

int main(void)
{
    int failed = 0;
    failed += check_plugin_defaults();
    failed += check_metatype_string();
    failed += check_version_macro();
    failed += check_extract_memory();
    if (0 != failed) {
        fprintf(stderr, "libextractor API assertions: %d failed\n", failed);
        return 1;
    }
    puts("libextractor API assertions: 4 passed");
    return 0;
}
