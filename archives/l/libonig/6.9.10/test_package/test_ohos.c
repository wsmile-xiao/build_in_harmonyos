#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "oniguruma.h"

#if !defined(__OHOS__)
#error "This test must be compiled for HarmonyOS"
#endif

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: HarmonyOS %s\n", message);
    return 1;
}

int main(void)
{
    const UChar pattern[] = "(?i)harmonyos";
    const UChar text[] = "HarmonyOS PC";
    const char *tmpdir = getenv("TMPDIR");
    char path[512];
    FILE *file;
    OnigEncoding encoding = ONIG_ENCODING_UTF8;
    OnigErrorInfo error_info;
    OnigRegion *region = NULL;
    regex_t *regex = NULL;
    int result;

    if (!tmpdir || !tmpdir[0]) {
        tmpdir = "/data/local/tmp";
    }
    if (snprintf(path, sizeof(path), "%s/libonig-ohos-%ld.txt", tmpdir,
                 (long)getpid()) >= (int)sizeof(path)) {
        return fail("temporary path is too long");
    }

    file = fopen(path, "wb");
    if (!file) {
        fprintf(stderr, "FAIL: HarmonyOS cannot write %s: %s\n", path,
                strerror(errno));
        return 1;
    }
    fputs("HarmonyOS PC\n", file);
    if (fclose(file) != 0) {
        remove(path);
        return fail("temporary file could not be closed");
    }

    file = fopen(path, "rb");
    if (!file) {
        remove(path);
        return fail("temporary file could not be reopened");
    }
    if (fgetc(file) != 'H') {
        fclose(file);
        remove(path);
        return fail("temporary file contents are incorrect");
    }
    fclose(file);

    if (onig_initialize(&encoding, 1) != 0) {
        remove(path);
        return fail("onig_initialize failed");
    }
    result = onig_new(&regex, pattern, pattern + sizeof(pattern) - 1,
                      ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8,
                      ONIG_SYNTAX_DEFAULT, &error_info);
    if (result != ONIG_NORMAL) {
        remove(path);
        onig_end();
        return fail("HarmonyOS expression compilation failed");
    }
    region = onig_region_new();
    result = onig_search(regex, text, text + sizeof(text) - 1, text,
                         text + sizeof(text) - 1, region, ONIG_OPTION_NONE);
    if (result < 0 || region == NULL || region->beg[0] != 0
        || region->end[0] != 9) {
        if (region != NULL) {
            onig_region_free(region, 1);
        }
        onig_free(regex);
        onig_end();
        remove(path);
        return fail("HarmonyOS API match failed");
    }

    onig_region_free(region, 1);
    onig_free(regex);
    onig_end();
    remove(path);
    puts("PASS: HarmonyOS Oniguruma API and /data/local/tmp-compatible storage");
    return 0;
}
