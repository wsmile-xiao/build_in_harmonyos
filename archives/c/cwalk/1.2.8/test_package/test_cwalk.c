#include <cwalk.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main(void) {
    char buffer[256];
    const char *basename;
    size_t length;
    int failures = 0;

    cwk_path_set_style(CWK_STYLE_UNIX);
    length = cwk_path_normalize("/opt/app/../data//file.txt", buffer,
                                sizeof(buffer));
    CHECK(length == strlen("/opt/data/file.txt"),
          "normalization reports the complete output length");
    CHECK(strcmp(buffer, "/opt/data/file.txt") == 0,
          "normalize a Unix path");

    cwk_path_join("/data/service", "../cache/item", buffer, sizeof(buffer));
    CHECK(strcmp(buffer, "/data/cache/item") == 0,
          "join and normalize Unix paths");

    cwk_path_get_relative("/data/service/app", "/data/cache/item", buffer,
                          sizeof(buffer));
    CHECK(strcmp(buffer, "../../cache/item") == 0,
          "derive a relative path");

    cwk_path_change_extension("archive.tar.gz", "xz", buffer, sizeof(buffer));
    CHECK(strcmp(buffer, "archive.tar.xz") == 0,
          "replace the final extension");

    cwk_path_get_basename("/data/cache/item.txt", &basename, &length);
    CHECK(length == strlen("item.txt") &&
          strncmp(basename, "item.txt", length) == 0,
          "read a basename without copying");

    cwk_path_set_style(CWK_STYLE_WINDOWS);
    cwk_path_normalize("C:\\work\\..\\data\\file.txt", buffer,
                       sizeof(buffer));
    CHECK(strcmp(buffer, "C:\\data\\file.txt") == 0,
          "normalize a Windows-style path");
    CHECK(cwk_path_is_absolute("C:\\data\\file.txt"),
          "recognize a Windows absolute path");

    cwk_path_set_style(CWK_STYLE_UNIX);
    if (failures != 0) {
        fprintf(stderr, "cwalk consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("cwalk consumer test passed: 8 assertions");
    return 0;
}
