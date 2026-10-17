/*
 * test_package/test.c — libsecret/0.20.5.1 loadability acceptance probe.
 *
 * WHY THIS DOES NOT LINK AGAINST libsecret
 * ----------------------------------------
 * The published libsecret/0.20.5 binary is rejected by the OHOS loader:
 *   dlopen("libsecret-1.so.0.0.0", RTLD_NOW)
 *     -> "Error loading shared library ...: Permission denied"   (EACCES)
 * while sibling chain libraries (libglib-2.0.so.0, libQt6Core.so.6,
 * libnm.so.0) load fine. Root cause is E077: the ELF carries a stale
 * `.codesign` section (the file was modified after the toolchain signed it),
 * and the HarmonyOS loader refuses an ELF whose signature does not verify.
 *
 * If this program linked against libsecret, the loader would resolve the
 * library at process start and a dlopen() would merely hand back the already
 * mapped object — which would hide exactly the defect we must catch. So the
 * probe is linked only against libdl and dlopen()s the *produced artifact*
 * explicitly with RTLD_NOW.
 *
 * R34: the probe additionally resolves and calls real `secret_*` API symbols
 * (secret_value_new / secret_value_get / secret_value_unref), so it cannot
 * pass as an empty print-only shell.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

/* SecretValue is opaque in the public API; only a forward declaration is
 * needed because every function is reached through dlsym(). */
typedef struct _SecretValue SecretValue;

typedef SecretValue *(*fn_secret_value_new)(const char *secret, ssize_t length,
                                            const char *content_type);
typedef const char *(*fn_secret_value_get)(SecretValue *value, size_t *length);
typedef void (*fn_secret_value_unref)(SecretValue *value);

/* Symbol-resolution-only surface: proves the exported API is really the
 * libsecret Secret Service API, without needing a D-Bus session bus. */
static const char *const api_surface[] = {
    "secret_value_new",
    "secret_value_get",
    "secret_value_get_text",
    "secret_value_unref",
    "secret_schema_new",
    "secret_schema_newv",
    "secret_password_store",
    "secret_password_lookup",
    "secret_service_get_sync",
    "secret_item_get_secret",
    "secret_collection_for_alias_sync",
    "secret_collection_for_alias_sync",
};

int main(int argc, char **argv)
{
    const char *lib = (argc > 1) ? argv[1] : "libsecret-1.so.0";
    void *handle;
    fn_secret_value_new value_new;
    fn_secret_value_get value_get;
    fn_secret_value_unref value_unref;
    SecretValue *value;
    const char *text;
    unsigned i, resolved = 0;
    int ok = 1;

    printf("ACCEPTANCE: dlopen(\"%s\", RTLD_NOW | RTLD_LOCAL)\n", lib);
    handle = dlopen(lib, RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        fprintf(stderr, "FAIL: dlopen(RTLD_NOW) rejected the produced artifact: %s\n",
                dlerror());
        return 1;
    }
    printf("ACCEPTANCE: dlopen(RTLD_NOW) OK, handle=%p\n", handle);

    for (i = 0; i < sizeof(api_surface) / sizeof(api_surface[0]); i++) {
        if (dlsym(handle, api_surface[i]) != NULL) {
            resolved++;
        } else {
            fprintf(stderr, "  note: dlsym(%s) unresolved\n", api_surface[i]);
        }
    }
    printf("ACCEPTANCE: secret_* symbol resolution %u/%u\n",
           resolved, (unsigned)(sizeof(api_surface) / sizeof(api_surface[0])));
    if (resolved == 0) {
        fprintf(stderr, "FAIL: none of the secret_* symbols resolved\n");
        return 1;
    }

    value_new = (fn_secret_value_new)dlsym(handle, "secret_value_new");
    value_get = (fn_secret_value_get)dlsym(handle, "secret_value_get");
    value_unref = (fn_secret_value_unref)dlsym(handle, "secret_value_unref");
    if (value_new == NULL || value_get == NULL || value_unref == NULL) {
        fprintf(stderr, "FAIL: dlsym secret_value_* -> %s\n",
                dlerror() ? dlerror() : "()");
        return 1;
    }

    value = value_new("payload", -1, "text/plain");
    if (value == NULL) {
        fprintf(stderr, "FAIL: secret_value_new() returned NULL\n");
        return 1;
    }
    text = value_get(value, NULL);
    if (text == NULL || strcmp(text, "payload") != 0) {
        fprintf(stderr, "FAIL: secret_value_get() roundtrip mismatch (%s)\n",
                text ? text : "()");
        ok = 0;
    }
    value_unref(value);
    if (!ok) {
        return 1;
    }

    printf("ACCEPTANCE: secret_value_new/get/unref roundtrip OK\n");
    printf("RESULT: libsecret-1.so.0 loaded with RTLD_NOW and secret_* API callable\n");
    return 0;
}
