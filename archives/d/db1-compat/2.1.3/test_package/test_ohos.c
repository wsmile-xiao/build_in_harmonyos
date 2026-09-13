#include <db.h>

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef __OHOS__
#error "HarmonyOS-specific test must be compiled by the OHOS toolchain"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC package must target AArch64"
#endif

#define REQUIRE(condition, message)                                          \
    do {                                                                     \
        if (!(condition)) {                                                  \
            fprintf(stderr, "OHOS FAIL: %s (line %d)\n", message, __LINE__); \
            return 1;                                                        \
        }                                                                    \
    } while (0)

int main(void)
{
    const char *path = "db1-ohos-abi.db";
    char key_text[] = "ohos-aarch64";
    char value_text[] = "persistent-value";
    DBT key = {key_text, sizeof(key_text)};
    DBT value = {value_text, sizeof(value_text)};
    DBT fetched;
    struct stat st;
    DB *db;
    int fd;

    REQUIRE(sizeof(void *) == 8, "OHOS AArch64 pointer ABI is 64-bit");
    REQUIRE(sizeof(off_t) == 8, "OHOS file offsets are 64-bit");

    db = dbopen(path, O_CREAT | O_TRUNC | O_RDWR, 0600, DB_BTREE, NULL);
    REQUIRE(db != NULL, "dbopen works with the OHOS libc ABI");
    REQUIRE(db->put(db, &key, &value, 0) == RET_SUCCESS,
            "write through the OHOS filesystem ABI");
    fd = db->fd(db);
    REQUIRE(fd >= 0, "DB exposes a valid OHOS file descriptor");
    REQUIRE(db->sync(db, 0) == RET_SUCCESS, "database sync succeeds on OHOS");
    REQUIRE(fstat(fd, &st) == 0 && st.st_size > 0,
            "database descriptor supports OHOS fstat");
    REQUIRE(db->close(db) == RET_SUCCESS, "database close succeeds on OHOS");

    db = dbopen(path, O_RDONLY, 0, DB_BTREE, NULL);
    REQUIRE(db != NULL, "persistent database reopens read-only on OHOS");
    REQUIRE(db->get(db, &key, &fetched, 0) == RET_SUCCESS,
            "persistent value is readable on OHOS");
    REQUIRE(fetched.size == sizeof(value_text) &&
                memcmp(fetched.data, value_text, sizeof(value_text)) == 0,
            "persistent value is unchanged on OHOS");
    REQUIRE(db->close(db) == RET_SUCCESS, "read-only database closes on OHOS");

    unlink(path);
    puts("HarmonyOS AArch64 db1-compat test passed (12 assertions)");
    return 0;
}
