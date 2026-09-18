#include <plist/plist.h>

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#if !defined(__OHOS__)
#error "This test must be compiled for HarmonyOS"
#endif

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void)
{
    const int64_t expected_date = INT64_C(-2208988800);
    const char *tmpdir = getenv("TMPDIR");
    char path[512];
    int64_t actual_date = 0;
    plist_t date = NULL;
    plist_t root = NULL;
    plist_t parsed = NULL;

    if (!tmpdir || !tmpdir[0]) {
        tmpdir = "/data/local/tmp";
    }
    if (snprintf(path, sizeof(path), "%s/libplist-2.7.0-ohos.plist", tmpdir)
        >= (int)sizeof(path)) {
        return fail("temporary path is too long");
    }

    date = plist_new_unix_date(expected_date);
    if (!date) {
        return fail("plist_new_unix_date returned NULL");
    }
    plist_get_unix_date_val(date, &actual_date);
    if (actual_date != expected_date) {
        plist_free(date);
        return fail("Unix date round-trip changed the timestamp");
    }

    root = plist_new_dict();
    if (!root) {
        plist_free(date);
        return fail("plist_new_dict returned NULL");
    }
    plist_dict_set_item(root, "harmony_unix_date", date);

    if (plist_write_to_file(root, path, PLIST_FORMAT_XML, PLIST_OPT_NONE) != PLIST_ERR_SUCCESS) {
        plist_free(root);
        return fail("plist_write_to_file failed in the HarmonyOS temp directory");
    }
    if (plist_read_from_file(path, &parsed, NULL) != PLIST_ERR_SUCCESS || !parsed) {
        unlink(path);
        plist_free(root);
        return fail("plist_read_from_file failed in the HarmonyOS temp directory");
    }

    date = plist_dict_get_item(parsed, "harmony_unix_date");
    if (!date) {
        unlink(path);
        plist_free(parsed);
        plist_free(root);
        return fail("HarmonyOS plist file did not contain the Unix date");
    }
    actual_date = 0;
    plist_get_unix_date_val(date, &actual_date);
    unlink(path);
    plist_free(parsed);
    plist_free(root);

    if (actual_date != expected_date) {
        return fail("file round-trip changed the Unix timestamp");
    }

    printf("PASS: HarmonyOS Unix-date and temp-file test\n");
    return 0;
}
