#include <glib.h>
#include <stdio.h>
#include <string.h>
#ifndef TARGET_SO
#define TARGET_SO "libglib-2.0.so"
#endif
#ifndef STATIC_TEST
#include <dlfcn.h>
#endif
int main(void) {
    int errors = 0;
    gchar *s = g_strdup("ohos-glib");
    if (!s || strcmp(s, "ohos-glib") != 0) { fprintf(stderr, "FAIL: g_strdup\n"); errors++; } else { printf("OK: g_strdup\n"); }
    g_free(s);
#ifdef STATIC_TEST
    printf("OK: static build (skip dlopen, linked statically)\n");
#else
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "FAIL: dlopen %s: %s\n", TARGET_SO, dlerror()); errors++; } else { printf("OK: dlopen %s\n", TARGET_SO); dlclose(h); }
#endif
    return errors ? 1 : 0;
}
