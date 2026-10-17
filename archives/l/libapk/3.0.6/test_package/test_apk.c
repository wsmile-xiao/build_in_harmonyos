#include <stdio.h>
#include <string.h>
#include <apk/apk_blob.h>
#include <apk/apk_version.h>

#define CHECK(name, cond) do { \
    if (cond) { printf("CASE PASS %s\n", name); passed++; } \
    else { printf("CASE FAIL %s\n", name); } \
    total++; \
} while (0)

int main(void) {
    int passed = 0, total = 0;

    /* 1. version validate: well-formed apk version is accepted. */
    CHECK("version-validate",
        apk_version_validate(APK_BLOB_STRLIT("1.0.0-r0")) &&
        apk_version_validate(APK_BLOB_STRLIT("3.0.6")));

    /* 2. version compare: older < newer yields the LESS mask. */
    {
        int r = apk_version_compare(
            APK_BLOB_STRLIT("1.0.0-r0"), APK_BLOB_STRLIT("1.0.1-r0"));
        CHECK("version-compare", (r & APK_VERSION_LESS) != 0);
    }

    /* 3. version match: 2.16.1-r3 satisfies the >= bound. */
    CHECK("version-match",
        apk_version_match(APK_BLOB_STRLIT("2.16.1-r3"),
            apk_version_result_mask(">="), APK_BLOB_STRLIT("2.16.1-r3")));

    /* 4. blob contains: needle offset semantics from upstream blob tests. */
    CHECK("blob-contains",
        apk_blob_contains(APK_BLOB_STRLIT("bar foo"), APK_BLOB_STRLIT("foo")) == 4 &&
        apk_blob_contains(APK_BLOB_STRLIT(" foo "), APK_BLOB_STRLIT("bar")) == -1);

    printf("SUMMARY total=%d passed=%d failed=%d\n", total, passed, total - passed);
    return (passed == total) ? 0 : 1;
}
