/*
 * libconfigini HarmonyOS-specific test (鸿蒙专项测试).
 *
 * Verifies the library's public API on the OHOS platform:
 *  1. Parses the upstream sample INI file (etc/config.cnf content embedded
 *     inline so the test is self-contained and runs anywhere).
 *  2. Exercises flat (section-less) config support.
 *  3. Exercises error paths (missing section/key return codes), which
 *     exercise the platform libc/malloc behavior on OHOS.
 * Uses only the installed public header and normal link target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "configini.h"

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
        exit(1); \
    } \
} while (0)

int main(void)
{
    /* Write a representative INI sample into a temp file (TMPDIR-aware). */
    const char *sample =
        "# comment\n"
        "[SECT1]\n"
        "a=1\n"
        "b=2\n"
        "[SECT2]\n"
        "aa=11\n"
        "bb=22\n";

    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = ".";
    }
    char path[512];
    snprintf(path, sizeof(path), "%s/libconfigini-ohos-test.cnf", tmpdir);

    FILE *fp = fopen(path, "w");
    CHECK(fp != NULL, "fopen sample");
    fwrite(sample, 1, strlen(sample), fp);
    fclose(fp);

    /* Public API: parse the file */
    Config *cfg = NULL;
    CHECK(ConfigReadFile(path, &cfg) == CONFIG_OK, "ConfigReadFile sample");
    CHECK(ConfigGetSectionCount(cfg) == 2, "section count == 2");
    CHECK(ConfigGetKeyCount(cfg, "SECT1") == 2, "SECT1 keys == 2");

    /* Value read + default fallback on missing key */
    int v = 0;
    CHECK(ConfigReadInt(cfg, "SECT1", "a", &v, -1) == CONFIG_OK && v == 1, "SECT1.a == 1");
    CHECK(ConfigReadInt(cfg, "SECT1", "missing", &v, 42) == CONFIG_ERR_NO_KEY && v == 42,
          "missing key returns default");

    /* Missing section error path */
    CHECK(ConfigReadInt(cfg, "NOPE", "a", &v, 0) == CONFIG_ERR_NO_SECTION,
          "missing section returns CONFIG_ERR_NO_SECTION");

    /* Flat config (CONFIG_SECTION_FLAT) */
    Config *flat = ConfigNew();
    CHECK(ConfigAddString(flat, CONFIG_SECTION_FLAT, "k", "v") == CONFIG_OK, "flat add");
    char s[64];
    CHECK(ConfigReadString(flat, CONFIG_SECTION_FLAT, "k", s, sizeof(s), "") == CONFIG_OK
          && strcmp(s, "v") == 0, "flat read");

    ConfigFree(flat);
    ConfigFree(cfg);
    remove(path);

    printf("libconfigini ohos test: OK\n");
    return 0;
}
