/*
 * test_package consumer test for libmaxminddb 1.13.3 (OHOS aarch64)
 *
 * Real consumer validation: opens the upstream MaxMind-DB test database,
 * performs a real IP lookup and decodes real entry data through the
 * public MMDB_* API. Asserts on actual values from the decoder fixture.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <maxminddb.h>

#define DATA_DIR "data"

static int check_lookup(MMDB_s *mmdb) {
    const char *ip = "1.1.1.1";
    int gai_error = 0;
    int mmdb_error = 0;
    MMDB_lookup_result_s result = MMDB_lookup_string(mmdb, ip, &gai_error, &mmdb_error);
    if (gai_error != 0) {
        printf("FAIL: getaddrinfo error %d for %s\n", gai_error, ip);
        return 1;
    }
    if (mmdb_error != MMDB_SUCCESS) {
        printf("FAIL: MMDB lookup error %d for %s\n", mmdb_error, ip);
        return 1;
    }
    if (!result.found_entry) {
        printf("FAIL: no entry found for %s\n", ip);
        return 1;
    }
    printf("OK: lookup found entry for %s\n", ip);

    /* decode "array" field -> first element must be uint32 1 */
    MMDB_entry_data_s entry_data;
    int status = MMDB_get_value(&result.entry, &entry_data, "array", "0", NULL);
    if (status != MMDB_SUCCESS) {
        printf("FAIL: MMDB_get_value(array/0) status %d\n", status);
        return 1;
    }
    if (entry_data.type != MMDB_DATA_TYPE_UINT32 || entry_data.uint32 != 1) {
        printf("FAIL: array[0] expected uint32=1, got type=%d value=%u\n",
               entry_data.type, entry_data.uint32);
        return 1;
    }
    printf("OK: decoded array[0] = uint32 1\n");

    /* decode "utf8_string" field -> "unicode! ☯ - ♫" (matches upstream
     * dump_t.c expectations for the decoder fixture, 18 UTF-8 bytes) */
    status = MMDB_get_value(&result.entry, &entry_data, "utf8_string", NULL);
    if (status != MMDB_SUCCESS) {
        printf("FAIL: MMDB_get_value(utf8_string) status %d\n", status);
        return 1;
    }
    const char *expected_utf8 = "unicode! \xE2\x98\xAF - \xE2\x99\xAB";
    if (entry_data.type != MMDB_DATA_TYPE_UTF8_STRING ||
        entry_data.data_size != 18 ||
        memcmp(entry_data.utf8_string, expected_utf8, 18) != 0) {
        printf("FAIL: utf8_string expected 18-byte unicode string, got type=%d size=%d\n",
               entry_data.type, entry_data.data_size);
        return 1;
    }
    printf("OK: decoded utf8_string = \"unicode! \xe2\x98\xaf - \xe2\x99\xab\"\n");

    /* metadata: database type must be "Test" */
    const char *db_type = mmdb->metadata.database_type;
    if (db_type && strcmp(db_type, "Test") == 0) {
        printf("OK: metadata database_type = %s\n", db_type);
    } else {
        printf("WARN: metadata database_type = %s (not 'Test')\n", db_type ? db_type : "(null)");
    }

    MMDB_close(mmdb);
    return 0;
}

int main(void) {
    const char *lib_version = MMDB_lib_version();
    printf("libmaxminddb version: %s\n", lib_version);
    if (strcmp(lib_version, "1.13.3") != 0) {
        printf("FAIL: expected lib version 1.13.3, got %s\n", lib_version);
        return 1;
    }
    printf("OK: library version 1.13.3\n");

    char path[512];
    snprintf(path, sizeof(path), "%s/%s", DATA_DIR, "MaxMind-DB-test-decoder.mmdb");

    MMDB_s mmdb_storage;
    int mmdb_error = MMDB_open(path, MMDB_MODE_MMAP, &mmdb_storage);
    MMDB_s *mmdb = &mmdb_storage;
    if (mmdb_error != MMDB_SUCCESS) {
        printf("FAIL: MMDB_open(%s) error %d\n", path, mmdb_error);
        return 1;
    }
    printf("OK: opened %s (mmap mode)\n", path);

    int rc = check_lookup(mmdb);
    if (rc != 0) {
        return rc;
    }
    printf("ALL CONSUMER TESTS PASSED\n");
    return 0;
}