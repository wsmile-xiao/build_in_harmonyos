#include <stdio.h>
#include <string.h>
#include <libkmod.h>

/* R34: substantively exercise libkmod public API:
 * kmod_new / kmod_get_dirname / kmod_load_resources /
 * kmod_module_new_from_name / kmod_module_get_name. */
int main(void) {
    struct kmod_ctx *ctx;
    struct kmod_module *mod = NULL;
    const char *dirname;
    const char *name;

    ctx = kmod_new(NULL, NULL);
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: kmod_new() returned NULL\n");
        return 1;
    }

    /* kmod_get_dirname: module dir derived from kmod_new args (default /lib/modules). */
    dirname = kmod_get_dirname(ctx);
    if (dirname == NULL || dirname[0] != '/') {
        fprintf(stderr, "FAIL: kmod_get_dirname() returned '%s'\n",
                dirname ? dirname : "(null)");
        kmod_unref(ctx);
        return 1;
    }
    printf("kmod module dir: %s\n", dirname);

    /* Best-effort resource load (reads /proc/modules + module index). */
    kmod_load_resources(ctx);

    /* kmod_module_new_from_name: creates a module object without lookup;
     * get_name normalizes dashes to underscores. */
    if (kmod_module_new_from_name(ctx, "hello-harmony", &mod) != 0 || mod == NULL) {
        fprintf(stderr, "FAIL: kmod_module_new_from_name() failed\n");
        kmod_unref(ctx);
        return 1;
    }
    name = kmod_module_get_name(mod);
    if (name == NULL || strcmp(name, "hello_harmony") != 0) {
        fprintf(stderr, "FAIL: kmod_module_get_name() returned '%s'\n",
                name ? name : "(null)");
        kmod_module_unref(mod);
        kmod_unref(ctx);
        return 1;
    }
    printf("module name (normalized): %s\n", name);

    kmod_module_unref(mod);
    kmod_unref(ctx);
    printf("PASS: libkmod ctx/dirname/module-name OK\n");
    return 0;
}
