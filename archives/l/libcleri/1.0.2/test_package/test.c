#include <stdio.h>
#include <stdlib.h>
#include <cleri/cleri.h>

/* Substantive consumer test: build a tiny grammar with the API and parse
 * real input strings, asserting the parser's verdict (R34). */
int main(void)
{
    cleri_t * k_hi = cleri_keyword(0, "hi", 0);
    cleri_t * r_name = cleri_regex(0, "^(?:\"(?:[^\"]*)\")+");
    cleri_t * start = cleri_sequence(0, 2, k_hi, r_name);
    cleri_grammar_t * grammar = cleri_grammar(start, NULL);
    int failures = 0;

    if (grammar == NULL) {
        printf("FAIL: cleri_grammar returned NULL\n");
        return 1;
    }

    cleri_parse_t * pr = cleri_parse(grammar, "hi \"Iris\"");
    printf("parse 'hi \"Iris\"': %s\n", pr && pr->is_valid ? "true" : "false");
    if (pr == NULL || !pr->is_valid) {
        failures++;
    }
    cleri_parse_free(pr);

    pr = cleri_parse(grammar, "bye \"Iris\"");
    printf("parse 'bye \"Iris\"': %s\n", pr && pr->is_valid ? "true" : "false");
    if (pr == NULL || pr->is_valid) {
        failures++;
    }
    cleri_parse_free(pr);

    cleri_grammar_free(grammar);

    if (failures != 0) {
        printf("test_libcleri: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_libcleri: OK (2/2)\n");
    return 0;
}