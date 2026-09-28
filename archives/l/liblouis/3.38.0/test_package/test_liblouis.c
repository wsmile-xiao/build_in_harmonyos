#include <liblouis/liblouis.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const widechar original[] = {'a', 'b', 'c'};
    widechar braille[32] = {0};
    widechar restored[32] = {0};
    int input_length = 3;
    int braille_length = 32;
    int reverse_input_length;
    int restored_length = 32;
    int index;

    if (lou_version() == NULL || strstr(lou_version(), "3.38.0") == NULL) {
        fprintf(stderr, "unexpected liblouis version\n");
        return 1;
    }
    if (lou_charSize() != 2 && lou_charSize() != 4) {
        fprintf(stderr, "unexpected widechar size\n");
        return 1;
    }
    if (!lou_translateString("en-us-g1.ctb", original, &input_length,
                             braille, &braille_length, NULL, NULL, 0) ||
        input_length != 3 || braille_length <= 0) {
        fprintf(stderr, "forward Braille translation failed\n");
        lou_free();
        return 1;
    }
    reverse_input_length = braille_length;
    if (!lou_backTranslateString("en-us-g1.ctb", braille, &reverse_input_length,
                                 restored, &restored_length, NULL, NULL, 0) ||
        restored_length != 3) {
        fprintf(stderr, "back-translation failed\n");
        lou_free();
        return 1;
    }
    for (index = 0; index < 3; ++index) {
        if (restored[index] != original[index]) {
            fprintf(stderr, "round-trip mismatch at %d\n", index);
            lou_free();
            return 1;
        }
    }
    lou_free();
    puts("LIBLOUIS_CONSUMER_PASS");
    return 0;
}
