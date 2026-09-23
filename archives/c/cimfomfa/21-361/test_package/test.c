#include <tingea/array.h>
#include <tingea/ting.h>

#include <stdio.h>
#include <string.h>

static int compare_int(const void *lhs, const void *rhs)
{
    const int left = *(const int *)lhs;
    const int right = *(const int *)rhs;
    return (left > right) - (left < right);
}

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "check failed at line %d: %s\n", __LINE__,       \
                    #condition);                                               \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    mcxTing *text = mcxTingNew("Open");
    int values[] = {1, 3, 3, 7, 9};
    int key = 3;
    int *floor_value;
    int *ceil_value;

    CHECK(text != NULL);
    CHECK(text->len == 4);
    CHECK(strcmp(text->str, "Open") == 0);
    CHECK(mcxTingAppend(text, "Harmony") == text);
    CHECK(text->len == 11);
    CHECK(strcmp(text->str, "OpenHarmony") == 0);

    floor_value = mcxBsearchFloor(
        &key, values, sizeof(values) / sizeof(values[0]), sizeof(values[0]),
        compare_int);
    ceil_value = mcxBsearchCeil(
        &key, values, sizeof(values) / sizeof(values[0]), sizeof(values[0]),
        compare_int);
    CHECK(floor_value == &values[2]);
    CHECK(ceil_value == &values[1]);

    mcxTingFree(&text);
    CHECK(text == NULL);
    puts("cimfomfa consumer checks passed");
    return 0;
}
