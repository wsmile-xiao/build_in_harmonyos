#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "stroke.h"

static int assertions = 0;

static void check(int condition, const char *message)
{
    assertions++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(EXIT_FAILURE);
    }
}

static void recognize_line(int x1, int y1, int x2, int y2,
                           const char *expected, const char *name)
{
    char sequence[STROKE_MAX_SEQUENCE + 1] = {0};

    stroke_init();
    stroke_record(x1, y1);
    stroke_record(x2, y2);
    check(stroke_trans(sequence) != 0, name);
    check(strcmp(sequence, expected) == 0, name);
}

int main(void)
{
    char sequence[STROKE_MAX_SEQUENCE + 1] = {0};
    int i;

    check(STROKE_MAX_POINTS == 10000, "STROKE_MAX_POINTS public constant");
    check(STROKE_MIN_POINTS == 50, "STROKE_MIN_POINTS public constant");
    check(STROKE_MAX_SEQUENCE == 20, "STROKE_MAX_SEQUENCE public constant");
    check(STROKE_SCALE_RATIO == 4, "STROKE_SCALE_RATIO public constant");

    stroke_init();
    check(stroke_trans(sequence) == 0, "empty stroke must be rejected");
    check(strcmp(sequence, "0") == 0, "empty stroke rejection marker");

    stroke_init();
    for (i = 0; i < 10; ++i) {
        stroke_record(i, 0);
    }
    check(stroke_trans(sequence) == 0, "short stroke must be rejected");
    check(strcmp(sequence, "0") == 0, "short stroke rejection marker");

    recognize_line(0, 0, 100, 0, "456", "left-to-right horizontal stroke");
    recognize_line(100, 0, 0, 0, "654", "right-to-left horizontal stroke");
    recognize_line(0, 0, 0, 100, "258", "top-to-bottom vertical stroke");
    recognize_line(0, 100, 0, 0, "852", "bottom-to-top vertical stroke");
    recognize_line(0, 0, 100, 100, "159", "diagonal stroke");

    stroke_init();
    stroke_record(0, 0);
    stroke_record(100, 0);
    (void)stroke_trans(sequence);
    stroke_record(100, 0);
    stroke_record(0, 0);
    check(stroke_trans(sequence) != 0, "recognizer must be reusable");
    check(strcmp(sequence, "654") == 0, "reused recognizer sequence");

    printf("libstroke HarmonyOS test: %d assertions passed\n", assertions);
    return EXIT_SUCCESS;
}
