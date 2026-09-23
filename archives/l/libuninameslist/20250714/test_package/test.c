/* test_package consumer test for libuninameslist/20250714
 *
 * Calls the public C API (uninameslist.h) and asserts observable results:
 *   - uniNamesList_NamesListVersion() must return a non-empty version string
 *   - uniNamesList_name(0x41) must return "LATIN CAPITAL LETTER A"
 *   - uniNamesList_blockCount() must be > 0 and match UnicodeBlock symbol size
 *   - uniNamesList_blockNumber() / blockName() round-trip on a known codepoint
 */
#include <stdio.h>
#include <string.h>
#include <uninameslist.h>

static int failures = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (cond) {                                                   \
            printf("PASS: %s\n", msg);                                \
        } else {                                                      \
            printf("FAIL: %s\n", msg);                                \
            failures++;                                               \
        }                                                             \
    } while (0)

int main(void) {
    const char *ver = uniNamesList_NamesListVersion();
    const char *name_a = uniNamesList_name(0x41UL);
    int nblocks = uniNamesList_blockCount();
    int bn = uniNamesList_blockNumber(0x41UL);
    const char *bname = (bn >= 0) ? uniNamesList_blockName(bn) : NULL;

    printf("libuninameslist NamesList version: %s\n", ver ? ver : "(null)");
    printf("uniNamesList_name(0x41) = %s\n", name_a ? name_a : "(null)");
    printf("blockCount = %d, blockNumber(0x41) = %d, blockName = %s\n",
           nblocks, bn, bname ? bname : "(null)");

    CHECK(ver != NULL && ver[0] != '\0', "version string non-empty");
    CHECK(name_a != NULL && strcmp(name_a, "LATIN CAPITAL LETTER A") == 0,
          "name(0x41) == LATIN CAPITAL LETTER A");
    CHECK(nblocks > 0 && nblocks == UNICODE_BLOCK_MAX,
          "blockCount > 0 and == UNICODE_BLOCK_MAX");
    CHECK(bn >= 0, "blockNumber(0x41) found");
    CHECK(bname != NULL && strstr(bname, "Basic Latin") != NULL,
          "blockName(0x41) contains 'Basic Latin'");

    if (failures == 0) {
        printf("test_libuninameslist: ALL CHECKS PASSED\n");
        return 0;
    }
    printf("test_libuninameslist: %d CHECK(S) FAILED\n", failures);
    return 1;
}