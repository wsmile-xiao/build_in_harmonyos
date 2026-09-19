/* test_blkid.c - exercise the packaged libblkid API (offline subset).
 *
 * Uses only APIs that work without root privileges or real block devices:
 * blkid_get_library_version, blkid_encode_string, blkid_parse_tag_string,
 * blkid_get_cache(/dev/null), blkid_put_cache.
 */
#include <stdio.h>
#include <string.h>
#include <blkid/blkid.h>

int main(void)
{
    const char *ver = NULL;
    const char *date = NULL;
    char enc[128];
    char *type = NULL, *value = NULL;
    blkid_cache cache = NULL;

    /* 1. library version */
    if (blkid_get_library_version(&ver, &date) == -1 || ver == NULL) {
        fprintf(stderr, "FAIL: blkid_get_library_version\n");
        return 1;
    }
    printf("libblkid version: %s (%s)\n", ver, date ? date : "?");

    /* 2. udev-safe string encoding */
    memset(enc, 0, sizeof(enc));
    if (blkid_encode_string("safe-string_1.2", enc, sizeof(enc)) != 0) {
        fprintf(stderr, "FAIL: blkid_encode_string\n");
        return 1;
    }
    if (strcmp(enc, "safe-string_1.2") != 0) {
        fprintf(stderr, "FAIL: unexpected encoding: %s\n", enc);
        return 1;
    }
    memset(enc, 0, sizeof(enc));
    if (blkid_encode_string("sp ace+plus", enc, sizeof(enc)) != 0) {
        fprintf(stderr, "FAIL: blkid_encode_string (specials)\n");
        return 1;
    }
    if (strstr(enc, "sp\\x20ace") == NULL || strstr(enc, "+") == NULL) {
        fprintf(stderr, "FAIL: specials not encoded udev-safe: %s\n", enc);
        return 1;
    }
    printf("blkid_encode_string: '%s'\n", enc);

    /* 3. TAG=VALUE parsing */
    if (blkid_parse_tag_string("LABEL=myroot", &type, &value) != 0 ||
        !type || !value || strcmp(type, "LABEL") != 0 || strcmp(value, "myroot") != 0) {
        fprintf(stderr, "FAIL: blkid_parse_tag_string\n");
        return 1;
    }
    printf("blkid_parse_tag_string: LABEL=%s\n", value);

    /* 4. cache create/release with an empty cache file */
    if (blkid_get_cache(&cache, "/dev/null") != 0) {
        fprintf(stderr, "FAIL: blkid_get_cache(/dev/null)\n");
        return 1;
    }
    blkid_put_cache(cache);

    printf("PASS: libblkid API smoke test\n");
    return 0;
}
