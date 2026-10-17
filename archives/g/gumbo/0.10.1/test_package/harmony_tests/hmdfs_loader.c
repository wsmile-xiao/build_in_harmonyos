/* HarmonyOS PC: signed, private HMDFS library + UTF-8 filesystem consumer.
 * A Windows/Linux smoke run cannot produce this target-specific PASS marker. */
#ifndef __OHOS__
#error This test requires the native HarmonyOS toolchain
#endif
#ifndef __aarch64__
#error This test requires arm64 HarmonyOS PC
#endif
#include <gumbo.h>
#include <errno.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char html[] = "<!doctype html><p id=\"鸿蒙\">你好，HarmonyOS PC</p>";
    struct utsname platform;
    struct stat info, parent_info;
    char path[4096], loaded[sizeof(html)], library[4096];
    FILE *file = NULL;
    void *handle = NULL;
    GumboOutput *out = NULL;
    int rc = 1, exists = 0, stage = 1;
    GumboOutput *(*parse)(const char *) = NULL;
    void (*destroy)(const GumboOptions *, GumboOutput *) = NULL;
    const GumboOptions *options = NULL;
    if (argc != 3 || uname(&platform) || strcmp(platform.sysname, "HarmonyOS") ||
        strcmp(platform.machine, "aarch64") ||
        strncmp(argv[1], "/storage/Users/", 15) ||
        strncmp(argv[2], "/storage/Users/", 15)) goto cleanup;
    if (stat(argv[2], &parent_info) || !S_ISDIR(parent_info.st_mode)) goto cleanup;
    stage = 2;
    if (snprintf(path, sizeof(path), "%s/鸿蒙-解析输入-%ld.html", argv[2], (long)getpid()) >= (int)sizeof(path) ||
        snprintf(library, sizeof(library), "%s/libgumbo.so.1.0.0", argv[1]) >= (int)sizeof(library)) goto cleanup;
    stage = 3;
    file = fopen(path, "wx");
    if (!file) goto cleanup;
    exists = 1;
    stage = 4;
    if (fwrite(html, 1, sizeof(html) - 1, file) != sizeof(html) - 1 || fflush(file)) goto cleanup;
    if (fclose(file)) { file = NULL; goto cleanup; }
    file = NULL;
    stage = 5;
    if (stat(path, &info)) goto cleanup;
    fprintf(stdout, "file_uid=%lu parent_uid=%lu process_uid=%lu file_bytes=%lld expected_bytes=%zu\n",
            (unsigned long)info.st_uid, (unsigned long)parent_info.st_uid,
            (unsigned long)getuid(), (long long)info.st_size, sizeof(html) - 1);
    /* HMDFS projects file_manager ownership even for files created by the
     * current process. Bind the task parent owner plus exact-byte readback;
     * do not confuse that filesystem identity with process UID ownership. */
    if (info.st_uid != parent_info.st_uid || info.st_size != sizeof(html) - 1) goto cleanup;
    stage = 6;
    file = fopen(path, "rb");
    if (!file || fread(loaded, 1, sizeof(html) - 1, file) != sizeof(html) - 1) goto cleanup;
    loaded[sizeof(html) - 1] = '\0';
    if (fclose(file)) { file = NULL; goto cleanup; }
    file = NULL;
    if (strcmp(loaded, html)) goto cleanup;
    stage = 7;
    handle = dlopen(library, RTLD_NOW | RTLD_LOCAL);
    if (!handle) { fprintf(stderr, "dlopen: %s\n", dlerror()); goto cleanup; }
    stage = 8;
    parse = (GumboOutput *(*)(const char *))dlsym(handle, "gumbo_parse");
    destroy = (void (*)(const GumboOptions *, GumboOutput *))dlsym(handle, "gumbo_destroy_output");
    options = (const GumboOptions *)dlsym(handle, "kGumboDefaultOptions");
    if (!parse || !destroy || !options) goto cleanup;
    stage = 9;
    out = parse(loaded);
    if (!out || !out->root || out->root->type != GUMBO_NODE_ELEMENT) goto cleanup;
    GumboVector *children = &out->root->v.element.children;
    GumboNode *body = NULL;
    for (unsigned i = 0; i < children->length; ++i) {
        GumboNode *n = children->data[i];
        if (n && n->type == GUMBO_NODE_ELEMENT && n->v.element.tag == GUMBO_TAG_BODY) body = n;
    }
    stage = 10;
    if (!body || body->v.element.children.length != 1) goto cleanup;
    GumboNode *p = body->v.element.children.data[0];
    if (!p || p->type != GUMBO_NODE_ELEMENT || p->v.element.tag != GUMBO_TAG_P ||
        p->v.element.attributes.length != 1 || p->v.element.children.length != 1) goto cleanup;
    GumboAttribute *id = p->v.element.attributes.data[0];
    GumboNode *text = p->v.element.children.data[0];
    stage = 11;
    if (!id || strcmp(id->name, "id") || strcmp(id->value, "鸿蒙") ||
        !text || text->type != GUMBO_NODE_TEXT || strcmp(text->v.text.text, "你好，HarmonyOS PC")) goto cleanup;
    rc = 0;
cleanup:
    if (rc) fprintf(stderr, "harmony_failure_stage=%d errno=%d (%s)\n", stage, errno, strerror(errno));
    if (out && destroy) destroy(options, out);
    if (handle && dlclose(handle)) rc = 1;
    if (file && fclose(file)) rc = 1;
    if (exists && (unlink(path) || access(path, F_OK) == 0)) rc = 1;
    if (!rc) puts("HARMONY_TEST_PASS=1/1");
    else fputs("FAIL: native HMDFS signed-loader UTF-8 consumer\n", stderr);
    return rc;
}
