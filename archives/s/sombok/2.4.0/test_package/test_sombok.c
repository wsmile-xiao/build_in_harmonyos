/* Consumer test for libsombok on HarmonyOS PC.
 *
 * Uses the library the way a downstream consumer would: create a
 * linebreak object, run UAX #14 line breaking over an ASCII string and
 * assert that the broken lines still carry every input character.
 * Exit code is the verdict (0 = pass).
 */
#include "sombok.h"
#include <stdio.h>
#include <string.h>

int main(void)
{
    static const char text[] = "Hello World, sombok works on HarmonyOS PC!";
    size_t n = sizeof(text) - 1;
    unichar_t buf[128];
    size_t i;

    for (i = 0; i < n; i++)
        buf[i] = (unichar_t)(unsigned char)text[i];

    /* unistr_t = {str, len} — the input form of gcstring_t. */
    {
        unistr_t uni;
        gcstring_t **lines;
        linebreak_t *lb;
        size_t nlines = 0, total = 0, j;

        uni.str = buf;
        uni.len = n;

        lb = linebreak_new(NULL);
        if (lb == NULL) {
            fprintf(stderr, "FAIL: linebreak_new returned NULL\n");
            return 2;
        }
        linebreak_set_format(lb, linebreak_format_SIMPLE, NULL);
        linebreak_set_sizing(lb, linebreak_sizing_UAX11, NULL);

        lines = linebreak_break(lb, &uni);
        if (lines == NULL) {
            fprintf(stderr, "FAIL: linebreak_break returned NULL\n");
            linebreak_destroy(lb);
            return 3;
        }

        for (j = 0; lines[j] != NULL; j++) {
            total += lines[j]->len;
            nlines++;
            gcstring_destroy(lines[j]);
        }
        linebreak_destroy(lb);

        if (nlines == 0 || total != n) {
            fprintf(stderr, "FAIL: nlines=%zu total=%zu expected=%zu\n",
                    nlines, total, n);
            return 4;
        }
        printf("OK: %zu line(s), %zu chars preserved\n", nlines, total);
    }
    return 0;
}
