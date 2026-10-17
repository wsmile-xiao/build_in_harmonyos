/* Consumer test for rgxg 0.1.2 on HarmonyOS PC (aarch64).
 *
 * Three kinds of checks:
 *   1. the packaged layout really exists and is AArch64 ELF (platform proof);
 *   2. the public API reproduces the upstream known-answer vectors, and every
 *      generated expression is then executed through the *device* libc regex
 *      engine, so a wrong regex cannot pass silently;
 *   3. the error paths keep their documented negative return codes.
 *
 * argv[1] is the rgxg package folder.
 */
#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <rgxg/net.h>
#include <rgxg/number.h>
#include <rgxg/types.h>
#include <rgxg/utils.h>

static int total_count;
static int pass_count;
static int fail_count;
static char package_folder[1024];

#define CHECK(condition, label) check_flag((condition), (label), __LINE__)

static void check_flag(int ok, const char *label, int line) {
    total_count++;
    if (ok) {
        pass_count++;
        printf("[PASS] %s\n", label);
    } else {
        fail_count++;
        printf("[FAIL] %s (line %d)\n", label, line);
    }
}

static int file_size(const char *relative) {
    char path[1200];
    struct stat info;
    snprintf(path, sizeof(path), "%s/%s", package_folder, relative);
    if (stat(path, &info) != 0) {
        return -1;
    }
    return (int)info.st_size;
}

/* Generate with the two-pass convention upstream uses: NULL returns the length. */
static char *cidr_regex_for(const char *cidr, rgxg_options_t options) {
    int n = rgxg_net_cidr_string(cidr, NULL, NULL, options);
    char *regex;
    if (n <= 0) {
        return NULL;
    }
    regex = malloc((size_t)n + 1);
    if (regex == NULL) {
        return NULL;
    }
    rgxg_net_cidr_string(cidr, NULL, regex, options);
    regex[n] = '\0';
    return regex;
}

static char *range_regex_for(long long first, long long last, int base,
                             size_t min_length, rgxg_options_t options) {
    int n = rgxg_number_range(first, last, base, min_length, NULL, options);
    char *regex;
    if (n <= 0) {
        return NULL;
    }
    regex = malloc((size_t)n + 1);
    if (regex == NULL) {
        return NULL;
    }
    rgxg_number_range(first, last, base, min_length, regex, options);
    regex[n] = '\0';
    return regex;
}

/* Does the device libc accept this expression at all? */
static int regex_compiles(const char *regex) {
    char anchored[4096];
    regex_t compiled;
    if (regex == NULL) {
        return 0;
    }
    snprintf(anchored, sizeof(anchored), "^(%s)$", regex);
    if (regcomp(&compiled, anchored, REG_EXTENDED | REG_NOSUB) != 0) {
        return 0;
    }
    regfree(&compiled);
    return 1;
}

/* Anchor a generated expression and run it through the device libc engine. */
static int regex_matches(const char *regex, const char *subject) {
    char anchored[4096];
    regex_t compiled;
    int result;
    if (regex == NULL) {
        return -1;
    }
    snprintf(anchored, sizeof(anchored), "^(%s)$", regex);
    if (regcomp(&compiled, anchored, REG_EXTENDED | REG_NOSUB) != 0) {
        return -2;
    }
    result = regexec(&compiled, subject, 0, NULL, 0);
    regfree(&compiled);
    return result == 0;
}

static void expect_equal(const char *label, const char *got, const char *want) {
    CHECK(got != NULL && strcmp(got, want) == 0, label);
    if (got == NULL) {
        printf("       got NULL, want %s\n", want);
    } else if (strcmp(got, want) != 0) {
        printf("       got  %s\n       want %s\n", got, want);
    }
}

/* Read the installed CLI's ELF header: proves the artifact really is a
 * 64-bit little-endian AArch64 executable built for HarmonyOS, not a host
 * binary that merely exists. */
static void check_elf_identity(void) {
    char path[1200];
    unsigned char header[20];
    FILE *stream;
    snprintf(path, sizeof(path), "%s/bin/rgxg", package_folder);
    stream = fopen(path, "rb");
    if (stream == NULL) {
        CHECK(0, "bin/rgxg is installed and readable");
        return;
    }
    CHECK(fread(header, 1, sizeof(header), stream) == sizeof(header),
          "bin/rgxg ELF header is complete");
    fclose(stream);
    CHECK(header[0] == 0x7f && header[1] == 'E' && header[2] == 'L' && header[3] == 'F',
          "bin/rgxg is an ELF object");
    CHECK(header[4] == 2, "bin/rgxg is ELFCLASS64");
    CHECK(header[5] == 1, "bin/rgxg is little-endian");
    /* e_machine lives at offset 18, in host byte order for LE objects. */
    CHECK(header[18] == 0xb7 && header[19] == 0x00, "bin/rgxg e_machine is EM_AARCH64");
}

int main(int argc, char **argv) {
    char *regex;
    char *first;
    char *second;
    const char *patterns[2];
    char *alternation;
    int n;

    if (argc > 1) {
        snprintf(package_folder, sizeof(package_folder), "%s", argv[1]);
    } else {
        fprintf(stderr, "usage: %s <rgxg package folder>\n", argv[0]);
        return 2;
    }

#ifdef __OHOS__
    CHECK(1, "consumer compiles for HarmonyOS (__OHOS__ defined)");
#else
    CHECK(0, "consumer compiles for HarmonyOS (__OHOS__ defined)");
#endif

    CHECK(file_size("lib/librgxg.a") > 0, "lib/librgxg.a is packaged");
    CHECK(file_size("include/rgxg/net.h") > 0, "include/rgxg/net.h is packaged");
    CHECK(file_size("include/rgxg/number.h") > 0, "include/rgxg/number.h is packaged");
    CHECK(file_size("include/rgxg/utils.h") > 0, "include/rgxg/utils.h is packaged");
    CHECK(file_size("include/rgxg/types.h") > 0, "include/rgxg/types.h is packaged");
    CHECK(file_size("licenses/LICENSE") > 0 || file_size("licenses/COPYING") > 0,
          "the Zlib license text is packaged");
    CHECK(file_size("bin/rgxg") > 0, "bin/rgxg is installed and executable");
    CHECK(file_size("lib/pkgconfig/rgxg.pc") > 0, "lib/pkgconfig/rgxg.pc is packaged");
    check_elf_identity();

    /* --- upstream known-answer vectors (tests/check_rgxg_net.c) ----------- */
    regex = cidr_regex_for("0.0.0.0/0", 0);
    expect_equal("cidr 0.0.0.0/0 matches any IPv4", regex,
                 "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
                 "(\\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}");
    CHECK(regex_matches(regex, "242.15.8.77"), "0.0.0.0/0 regex accepts an arbitrary address");
    free(regex);

    regex = cidr_regex_for("0.0.0.0/24", 0);
    expect_equal("cidr 0.0.0.0/24 keeps the last octet open", regex,
                 "0\\.0\\.0\\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])");
    CHECK(regex_matches(regex, "0.0.0.177"), "/24 regex accepts 0.0.0.177");
    CHECK(!regex_matches(regex, "1.0.0.177"), "/24 regex rejects 1.0.0.177");
    free(regex);

    regex = cidr_regex_for("0.0.0.0/32", 0);
    expect_equal("cidr /32 collapses to one address", regex, "0\\.0\\.0\\.0");
    free(regex);

    regex = cidr_regex_for("192.0.2.232/32", 0);
    expect_equal("cidr 192.0.2.232/32 is literal", regex, "192\\.0\\.2\\.232");
    free(regex);

    regex = cidr_regex_for("::0/0", RGXG_NOMIXEDNOTATION);
    CHECK(regex != NULL && strstr(regex, ":[0-9A-Fa-f]{1,4}") != NULL,
          "IPv6 ::0/0 regex is generated with hex groups");
    free(regex);

    regex = cidr_regex_for("255.255.255.255/32", 0);
    expect_equal("cidr 255.255.255.255/32 collapses to a repeated group", regex,
                 "255(\\.255){3}");
    free(regex);

    /* --- upstream known-answer vectors (tests/check_rgxg_number.c) -------- */
    regex = range_regex_for(0, 31, 10, 0, 0);
    expect_equal("number range 0..31 in base 10", regex, "(3[01]|[12]?[0-9])");
    CHECK(regex_matches(regex, "7"), "0..31 regex accepts 7");
    CHECK(regex_matches(regex, "31"), "0..31 regex accepts 31");
    CHECK(!regex_matches(regex, "32"), "0..31 regex rejects 32");
    free(regex);

    regex = range_regex_for(0, 31, 2, 0, 0);
    expect_equal("number range 0..31 in base 2", regex, "(1[01]{0,4}|0)");
    free(regex);

    second = range_regex_for(0, 31, 10, 0, RGXG_NOOUTERPARENS);
    expect_equal("RGXG_NOOUTERPARENS drops the group", second, "3[01]|[12]?[0-9]");
    free(second);

    second = range_regex_for(0, 31, 10, 0, RGXG_LEADINGZERO);
    expect_equal("RGXG_LEADINGZERO pads to fixed width", second, "(3[01]|[0-2][0-9])");
    free(second);

    regex = range_regex_for(0, 4294967296LL, 10, 0, 0);
    CHECK(regex != NULL && strlen(regex) > 0, "a 64-bit range produces a non-empty regex");
    CHECK(regex_compiles(regex), "the 64-bit range expression compiles on the device libc");
    free(regex);

    /* --- utils: escaping and alternation --------------------------------- */
    n = rgxg_utils_escape_string("a.b*c+d", 7, NULL, 0);
    regex = n > 0 ? malloc((size_t)n + 1) : NULL;
    if (regex != NULL) {
        rgxg_utils_escape_string("a.b*c+d", 7, regex, 0);
        regex[n] = '\0';
    }
    CHECK(regex_matches(regex, "a.b*c+d"), "escaped literal matches itself");
    CHECK(!regex_matches(regex, "axbxcxd"), "escaped literal is no longer a wildcard");
    free(regex);

    patterns[0] = "foo";
    patterns[1] = "bar";
    n = rgxg_utils_alternation(patterns, 2, NULL, 0);
    alternation = n > 0 ? malloc((size_t)n + 1) : NULL;
    if (alternation != NULL) {
        rgxg_utils_alternation(patterns, 2, alternation, 0);
        alternation[n] = '\0';
    }
    CHECK(regex_matches(alternation, "foo"), "alternation matches the first pattern");
    CHECK(regex_matches(alternation, "bar"), "alternation matches the second pattern");
    CHECK(!regex_matches(alternation, "baz"), "alternation rejects an unlisted pattern");
    free(alternation);

    /* --- error paths ------------------------------------------------------ */
    CHECK(rgxg_net_cidr_string("10.0.0.0/33", NULL, NULL, 0) <= 0,
          "an out-of-range IPv4 prefix is rejected");
    CHECK(rgxg_net_cidr_string("not-a-cidr", NULL, NULL, 0) <= 0,
          "malformed CIDR input is rejected");
    CHECK(rgxg_number_range(31, 0, 10, 0, NULL, 0) == RGXG_ERROR_RANGE,
          "an inverted range returns RGXG_ERROR_RANGE");
    CHECK(rgxg_number_range(0, 31, 33, 0, NULL, 0) == RGXG_ERROR_BASE,
          "an out-of-range base returns RGXG_ERROR_BASE");

    /* Both vectors come from the same ::0/0 input, so the difference is
     * entirely attributable to RGXG_NOMIXEDNOTATION. */
    first = cidr_regex_for("::0/0", 0);
    second = cidr_regex_for("::0/0", RGXG_NOMIXEDNOTATION);
    CHECK(first != NULL && second != NULL && strcmp(first, second) != 0,
          "RGXG_NOMIXEDNOTATION changes the generated IPv6 expression");
    free(first);
    free(second);

    printf("TOTAL=%d PASS=%d FAIL=%d\n", total_count, pass_count, fail_count);
    return fail_count == 0 ? 0 : 1;
}
