#include <smaz.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main(void) {
    char compressed[512];
    char restored[512];
    int comprlen;
    int decomprlen;
    int failures = 0;

    const char *english = "This is a small string";
    comprlen = smaz_compress((char *)english, (int)strlen(english),
                             compressed, (int)sizeof(compressed));
    CHECK(comprlen > 0 && comprlen < (int)strlen(english),
          "compress a short English string into fewer bytes");

    decomprlen = smaz_decompress(compressed, comprlen,
                                 restored, (int)sizeof(restored));
    CHECK(decomprlen == (int)strlen(english) &&
          memcmp(english, restored, strlen(english)) == 0,
          "round-trip the English string losslessly");

    const char *url = "http://github.com/antirez/smaz/tree/master";
    comprlen = smaz_compress((char *)url, (int)strlen(url),
                             compressed, (int)sizeof(compressed));
    decomprlen = smaz_decompress(compressed, comprlen,
                                 restored, (int)sizeof(restored));
    CHECK(decomprlen == (int)strlen(url) &&
          memcmp(url, restored, strlen(url)) == 0,
          "round-trip a URL losslessly");

    const char binary[] = {
        (char)0x00, (char)0xfe, (char)0xff, (char)0x80, (char)0x7f, 'A'
    };
    comprlen = smaz_compress((char *)binary, (int)sizeof(binary),
                             compressed, (int)sizeof(compressed));
    CHECK(comprlen > 0, "compress binary data containing opcode-range bytes");

    decomprlen = smaz_decompress(compressed, comprlen,
                                 restored, (int)sizeof(restored));
    CHECK(decomprlen == (int)sizeof(binary) &&
          memcmp(binary, restored, sizeof(binary)) == 0,
          "round-trip binary data losslessly");

    comprlen = smaz_compress((char *)"", 0, compressed, (int)sizeof(compressed));
    CHECK(comprlen == 0, "compressing an empty input yields an empty output");
    decomprlen = smaz_decompress(compressed, 0, restored, (int)sizeof(restored));
    CHECK(decomprlen == 0, "decompressing an empty input yields an empty output");

    char single = 'x';
    comprlen = smaz_compress(&single, 1, compressed, (int)sizeof(compressed));
    decomprlen = smaz_decompress(compressed, comprlen,
                                 restored, (int)sizeof(restored));
    CHECK(decomprlen == 1 && restored[0] == 'x',
          "round-trip a single character");

    const char *long_text =
        "Nothing is more difficult, and therefore more precious, "
        "than to be able to decide";
    comprlen = smaz_compress((char *)long_text, (int)strlen(long_text),
                             compressed, (int)sizeof(compressed));
    decomprlen = smaz_decompress(compressed, comprlen, restored, 1);
    CHECK(decomprlen == 1 + 1,
          "an undersized output buffer reports outlen+1 as documented");

    if (failures != 0) {
        fprintf(stderr, "smaz consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("smaz consumer test passed: 8 assertions");
    return 0;
}
