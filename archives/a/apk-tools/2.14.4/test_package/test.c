// test_apk.c — apk-tools L1 test for libapk C API.
//
// Verifies libapk links and a pure parsing API works at runtime:
// apk_pkg_parse_name() splits "name-version" into name/version blobs —
// no apk database / network / real device required (R34: substantive use
// of the tested library's API).
#include <apk/apk_blob.h>
#include <apk/apk_package.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 断言 1: apk_pkg_parse_name 可解析 "zlib-1.3.1"（name=zlib, version=1.3.1） */
    apk_blob_t apkname = APK_BLOB_STR("zlib-1.3.1");
    apk_blob_t name = APK_BLOB_NULL;
    apk_blob_t version = APK_BLOB_NULL;

    int ret = apk_pkg_parse_name(apkname, &name, &version);
    if (ret != 0) {
        printf("apk_pkg_parse_name: FAILED (ret=%d)\n", ret);
        return 1;
    }
    printf("apk_pkg_parse_name: name='%.*s' version='%.*s'\n",
           (int)name.len, name.ptr, (int)version.len, version.ptr);

    if (name.len != 4 || memcmp(name.ptr, "zlib", 4) != 0) {
        printf("FAIL: name != 'zlib'\n");
        return 1;
    }
    if (version.len != 5 || memcmp(version.ptr, "1.3.1", 5) != 0) {
        printf("FAIL: version != '1.3.1'\n");
        return 1;
    }

    /* 断言 2: apk_version.h 宏可用（APK_VERSION_EQUAL 等由 libapk 头提供） */
#ifndef APK_VERSION_EQUAL
    printf("FAIL: APK_VERSION_EQUAL not defined\n");
    return 1;
#endif
    printf("APK_VERSION_EQUAL: %d\n", APK_VERSION_EQUAL);

    printf("test_apk: ALL PASS\n");
    return 0;
}
