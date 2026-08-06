#include <stdio.h>
#include "enca.h"

int main(void) {
    /* Get list of supported languages */
    size_t n_langs = 0;
    const char **langs = enca_get_languages(&n_langs);
    if (n_langs == 0 || langs == NULL) {
        fprintf(stderr, "FAIL: enca_get_languages returned 0 languages\n");
        return 1;
    }
    printf("enca supports %zu languages\n", n_langs);

    /* Allocate an analyser for Russian (a well-supported language) */
    EncaAnalyser analyser = enca_analyser_alloc("ru");
    if (analyser == NULL) {
        fprintf(stderr, "FAIL: enca_analyser_alloc(\"ru\") returned NULL\n");
        return 1;
    }
    printf("enca_analyser_alloc(\"ru\") succeeded\n");

    /* Analyse a sample of UTF-8 text */
    const unsigned char sample[] = {
        0xD0, 0x9F, 0xD1, 0x80, 0xD0, 0xB8, 0xD0, 0xB2,
        0xD0, 0xB5, 0xD1, 0x82, 0x20, 0xD0, 0xBC, 0xD0,
        0xB8, 0xD1, 0x80  /* "Привет мир" (Hello world) in UTF-8 */
    };
    EncaEncoding enc = enca_analyse_const(analyser, sample, sizeof(sample));
    if (enc.charset == ENCA_CS_UNKNOWN) {
        fprintf(stderr, "FAIL: enca_analyse_const returned ENCA_CS_UNKNOWN\n");
        enca_analyser_free(analyser);
        return 1;
    }

    const char *cs_name = enca_charset_name(enc.charset, ENCA_NAME_STYLE_ENCA);
    printf("Detected charset: %s (id=%d)\n", cs_name ? cs_name : "(null)", enc.charset);

    enca_analyser_free(analyser);
    printf("test enca 1.19: OK\n");
    return 0;
}
