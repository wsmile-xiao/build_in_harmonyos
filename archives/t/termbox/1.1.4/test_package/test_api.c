#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <termbox.h>

static int checks;
static int failures;

static void check(int condition, const char *message)
{
    ++checks;
    if (!condition) {
        ++failures;
        fprintf(stderr, "FAIL: %s\n", message);
    }
}

static void check_roundtrip(uint32_t codepoint, const char *expected, int length)
{
    char encoded[8] = {0};
    uint32_t decoded = 0;

    check(tb_utf8_unicode_to_char(encoded, codepoint) == length,
          "unicode-to-UTF-8 length");
    check(memcmp(encoded, expected, (size_t)length) == 0,
          "unicode-to-UTF-8 bytes");
    check(tb_utf8_char_to_unicode(&decoded, encoded) == length,
          "UTF-8-to-unicode length");
    check(decoded == codepoint, "UTF-8 roundtrip code point");
}

int main(void)
{
    uint32_t decoded = 1;

    check(tb_width() < 0, "width is negative before initialization");
    check(tb_height() < 0, "height is negative before initialization");
    check(tb_utf8_char_length('A') == 1, "ASCII length");
    check(tb_utf8_char_length((char)0xC2) == 2, "two-byte UTF-8 length");
    check(tb_utf8_char_length((char)0xE4) == 3, "three-byte UTF-8 length");
    check(tb_utf8_char_length((char)0xF0) == 4, "four-byte UTF-8 length");
    check(tb_utf8_char_to_unicode(&decoded, "") == TB_EOF,
          "empty string reports TB_EOF");
    check(TB_KEY_ARROW_UP != TB_KEY_ARROW_DOWN, "key constants are distinct");
    check_roundtrip(0x41, "A", 1);
    check_roundtrip(0x4F60, "\xE4\xBD\xA0", 3);

    if (failures != 0) {
        fprintf(stderr, "termbox API: %d/%d checks failed\n", failures, checks);
        return 1;
    }

    printf("termbox API: PASS (%d assertions)\n", checks);
    return 0;
}
