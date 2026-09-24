#include <libdockapp/dockapp.h>
#include <libdockapp/list.h>
#include <libdockapp/misc.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int assertions;
static int failures;
static int mapped_sum;

#define CHECK(condition, label)                                                \
    do {                                                                       \
        ++assertions;                                                          \
        if (!(condition)) {                                                    \
            ++failures;                                                        \
            fprintf(stderr, "not ok %d - %s\n", assertions, (label));        \
        } else {                                                               \
            printf("ok %d - %s\n", assertions, (label));                    \
        }                                                                      \
    } while (0)

static void sum_value(void *value)
{
    mapped_sum += *(int *)value;
}

int main(void)
{
    Display *display = (Display *)(uintptr_t)0x1000;
    Visual *visual = (Visual *)(uintptr_t)0x2000;
    int one = 1;
    int two = 2;
    int three = 3;
    LinkedList *list = NULL;
    char command[] = "alpha \"two words\" 'three words'";
    char **argv = NULL;
    int argc = 0;
    int index;

    CHECK(DA_VERSION == 20050716, "public ABI version constant");
    DASetExpectedVersion(DA_VERSION);
    CHECK(DAExpectedVersion == DA_VERSION, "expected version setter");
    DASetDisplay(display);
    CHECK(DAGetDisplay(NULL) == display, "display setter/getter");
    DASetWindow((Window)11);
    CHECK(DAGetWindow() == (Window)11, "window setter/getter");
    DASetLeader((Window)12);
    CHECK(DAGetLeader() == (Window)12, "leader setter/getter");
    DASetIconWindow((Window)13);
    CHECK(DAGetIconWindow() == (Window)13, "icon setter/getter");
    DASetDepth(32);
    CHECK(DAGetDepth() == 32, "depth setter/getter");
    DASetVisual(visual);
    CHECK(DAGetVisual() == visual, "visual setter/getter");

    CHECK(list_length(NULL) == 0, "empty list length");
    list = list_cons(&three, list);
    list = list_cons(&two, list);
    list = list_cons(&one, list);
    CHECK(list_length(list) == 3, "populated list length");
    CHECK(list_nth(0, list) == &one, "first list element");
    CHECK(list_nth(1, list) == &two, "second list element");
    CHECK(list_nth(2, list) == &three, "third list element");
    CHECK(list_nth(3, list) == NULL, "out-of-range list lookup");
    CHECK(list_find(list, &two) != NULL, "find list element");
    list_mapcar(list, sum_value);
    CHECK(mapped_sum == 6, "map over list elements");
    list = list_remove_elem(list, &two);
    CHECK(list_length(list) == 2, "remove list element");
    CHECK(list_find(list, &two) == NULL, "removed element is absent");
    list_remove_head(&list);
    CHECK(list_length(list) == 1, "remove list head");
    CHECK(list->head == &three, "remaining list value");
    list_free(list);

    parse_command(command, &argv, &argc);
    CHECK(argc == 3, "command token count");
    CHECK(strcmp(argv[0], "alpha") == 0, "plain command token");
    CHECK(strcmp(argv[1], "two words") == 0, "double-quoted command token");
    CHECK(strcmp(argv[2], "three words") == 0, "single-quoted command token");
    for (index = 0; index < argc; ++index)
        free(argv[index]);
    free(argv);

#ifdef __OHOS__
    CHECK(sizeof(void *) == 8, "HarmonyOS PC aarch64 pointer width");
#endif

    printf("libdockapp: %d assertions, %d failures\n", assertions, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
