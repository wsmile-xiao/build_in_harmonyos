/* test_package/test.c — uchardet 0.0.7 consumer test (R34: real API calls).
 *
 * Feeds byte sequences with known encodings through the public C API
 * (uchardet_new/handle_data/data_end/get_charset/reset/delete) and asserts
 * the detected charset names.  All samples and expected results were
 * verified against the locally built upstream CLI on OHOS before being
 * embedded here.
 */
#include <stdio.h>
#include <string.h>

#include <uchardet/uchardet.h>

static int failures = 0;

static void check_detection(const char *label, const char *data, size_t len,
                            const char *expected)
{
    uchardet_t ud = uchardet_new();
    if (ud == NULL) {
        fprintf(stderr, "FAIL %s: uchardet_new returned NULL\n", label);
        failures++;
        return;
    }

    if (uchardet_handle_data(ud, data, len) != 0) {
        fprintf(stderr, "FAIL %s: uchardet_handle_data returned error\n", label);
        failures++;
        uchardet_delete(ud);
        return;
    }
    uchardet_data_end(ud);

    const char *cs = uchardet_get_charset(ud);
    if (strcmp(cs, expected) != 0) {
        fprintf(stderr, "FAIL %s: expected \"%s\", got \"%s\"\n",
                label, expected, cs);
        failures++;
    } else {
        printf("PASS %s -> \"%s\"\n", label, cs);
    }

    /* uchardet_reset must return the handle to a reusable state: re-feed
     * the same data and expect the same detection result. */
    uchardet_reset(ud);
    if (uchardet_handle_data(ud, data, len) != 0) {
        fprintf(stderr, "FAIL %s: uchardet_handle_data after reset failed\n", label);
        failures++;
    }
    uchardet_data_end(ud);
    const char *cs2 = uchardet_get_charset(ud);
    if (strcmp(cs2, expected) != 0) {
        fprintf(stderr, "FAIL %s: after reset expected \"%s\", got \"%s\"\n",
                label, expected, cs2);
        failures++;
    }

    uchardet_delete(ud);
}

int main(void)
{
    /* Plain ASCII (verified: "ASCII"). */
    static const char ascii[] =
        "The quick brown fox jumps over the lazy dog.\n"
        "Pack my box with five dozen liquor jugs.\n";

    /* UTF-8 encoded Chinese text (verified: "UTF-8"). */
    static const char utf8[] =
        "\xe4\xb8\xad\xe6\x96\x87\xe7\xbc\x96\xe7\xa0\x81\xe6\xa3\x80\xe6\xb5\x8b"
        "\xe6\xb5\x8b\xe8\xaf\x95\xe6\x96\x87\xe6\x9c\xac\xef\xbc\x8c\xe8\xbf\x99"
        "\xe6\x98\xaf\xe4\xb8\x80\xe4\xb8\xaa\xe7\x94\xa8\xe4\xba\x8e\xe5\xad\x97"
        "\xe7\xac\xa6\xe9\x9b\x86\xe6\xa3\x80\xe6\xb5\x8b\xe7\x9a\x84\xe7\xa4\xba"
        "\xe4\xbe\x8b\xe6\xae\xb5\xe8\x90\xbd\xef\xbc\x8c\xe5\x8c\x85\xe5\x90\xab"
        "\xe8\xb6\xb3\xe5\xa4\x9f\xe5\xa4\x9a\xe7\x9a\x84\xe5\xad\x97\xe7\xac\xa6"
        "\xe7\x94\xa8\xe4\xba\x8e\xe5\x88\xa4\xe6\x96\xad\xe3\x80\x82\n";

    /* GBK/GB18030 double-byte Chinese (verified: "GB18030"). */
    static const char gb[] =
        "\xd6\xd0\xce\xc4\xb2\xe2\xca\xd4\xd5\xe2\xb6\xce\xce\xc4\xd7\xd6"
        "\xb5\xc4\xb1\xe0\xc2\xeb\xb7\xbd\xca\xbd\xca\xc7\x47\x42\x4b\xd3\xc3"
        "\xd3\xda\xbc\xec\xb2\xe2\xb5\xc4\xc1\xed\xd2\xbb\xb6\xce\xd1\xf9\xb1\xbe\n";

    /* Big5 encoded Chinese (verified: "BIG5"). */
    static const char big5[] =
        "\xa4\xa4\xa4\xe5\xb4\xfa\xb8\xd5\xb3\x71\xa6\x73\xba\x69\xac\x71\n"
        "\xb3\x6f\xac\x4f\xa5\xce\xa9\xf3\xbd\xd5\xb4\xfa\xaa\xba\xa8\xe2\xba\x71\n";

    check_detection("ascii", ascii, sizeof(ascii) - 1, "ASCII");
    check_detection("utf-8", utf8, sizeof(utf8) - 1, "UTF-8");
    check_detection("gb18030", gb, sizeof(gb) - 1, "GB18030");
    check_detection("big5", big5, sizeof(big5) - 1, "BIG5");

    if (failures > 0) {
        fprintf(stderr, "%d detection check(s) FAILED\n", failures);
        return 1;
    }
    printf("All uchardet detection checks passed\n");
    return 0;
}
