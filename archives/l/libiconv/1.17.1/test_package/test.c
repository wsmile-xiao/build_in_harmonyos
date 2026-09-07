#include <errno.h>
#include <iconv.h>
#include <stdio.h>
#include <string.h>

static int convert(const char *from, const char *to, const char *input,
                   size_t input_size, const unsigned char *expected,
                   size_t expected_size) {
    iconv_t cd = iconv_open(to, from);
    if (cd == (iconv_t)-1) {
        fprintf(stderr, "iconv_open(%s, %s) failed: %s\n", from, to,
                strerror(errno));
        return 1;
    }

    char output[128];
    char *inptr = (char *)input;
    char *outptr = output;
    size_t inbytes = input_size;
    size_t outbytes = sizeof(output);
    size_t result = iconv(cd, &inptr, &inbytes, &outptr, &outbytes);
    if (result != (size_t)-1)
        result = iconv(cd, NULL, NULL, &outptr, &outbytes);
    int failed = result == (size_t)-1 || inbytes != 0 ||
                 (size_t)(outptr - output) != expected_size ||
                 memcmp(output, expected, expected_size) != 0;
    iconv_close(cd);

    if (failed) {
        fprintf(stderr, "conversion %s -> %s failed\n", from, to);
        return 1;
    }
    return 0;
}

int main(void) {
    static const unsigned char ascii[] = "Hello";
    static const unsigned char korean_utf8[] = "\xEC\x95\x88\xEB\x85\x95";
    static const unsigned char japanese_iso2022[] = "\x1B$B$3\x1B(B";
    static const char korean_euc_kr[] = "\xBE\xC8\xB3\xE7";
    static const char japanese_utf8[] = "\xE3\x81\x93";

    if (convert("UTF-8", "ASCII", "Hello", 5, ascii, sizeof(ascii) - 1) != 0)
        return 1;
    if (convert("EUC-KR", "UTF-8", korean_euc_kr, sizeof(korean_euc_kr) - 1,
                korean_utf8, sizeof(korean_utf8) - 1) != 0)
        return 1;
    if (convert("UTF-8", "ISO-2022-JP", japanese_utf8,
                sizeof(japanese_utf8) - 1, japanese_iso2022,
                sizeof(japanese_iso2022) - 1) != 0)
        return 1;

    puts("libiconv consumer tests passed: ASCII, EUC-KR and ISO-2022-JP");
    return 0;
}
