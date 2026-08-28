#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cxstring.h"
#include "cxslist.h"
#include "cxtypes.h"
#include "cxversion.h"

int main(void) {
    /* Assertion 1: cx_string create + set + size + content */
    cx_string *s = cx_string_new();
    if (!s) {
        fprintf(stderr, "cx_string_new failed\n");
        return 1;
    }
    cx_string_set(s, "HarmonyOS");
    if (cx_string_size(s) != 9) {
        fprintf(stderr, "size=%zu (expected 9)\n", cx_string_size(s));
        cx_string_delete(s);
        return 2;
    }
    if (strcmp(cx_string_get(s), "HarmonyOS") != 0) {
        fprintf(stderr, "content mismatch: %s\n", cx_string_get(s));
        cx_string_delete(s);
        return 3;
    }

    /* Assertion 2: cx_string append grows the size (state change) */
    cx_string_append(s, " libcext");
    if (cx_string_size(s) <= 9) {
        fprintf(stderr, "size did not grow after append: %zu\n",
                cx_string_size(s));
        cx_string_delete(s);
        return 4;
    }
    if (strstr(cx_string_get(s), "libcext") == NULL) {
        fprintf(stderr, "append content missing: %s\n", cx_string_get(s));
        cx_string_delete(s);
        return 5;
    }
    cx_string_delete(s);

    /* Assertion 3: cx_string_sprintf with the CX_VERSION_* symbols */
    cx_string *v = cx_string_new();
    if (!v) {
        fprintf(stderr, "cx_string_new failed (v)\n");
        return 6;
    }
    cx_string_sprintf(v, "libcext %d.%d.%d",
                      CX_VERSION_MAJOR, CX_VERSION_MINOR, CX_VERSION_MICRO);
    if (strcmp(cx_string_get(v), "libcext 1.3.2") != 0) {
        fprintf(stderr, "version string unexpected: %s\n", cx_string_get(v));
        cx_string_delete(v);
        return 7;
    }
    cx_string_delete(v);

    /* Assertion 4: cx_slist push_back/push_front grow size 0 -> 1 -> 2 -> 3 */
    cx_slist *list = cx_slist_new();
    if (!list) {
        fprintf(stderr, "cx_slist_new failed\n");
        return 8;
    }
    if (!cx_slist_empty(list)) {
        fprintf(stderr, "new list is not empty\n");
        cx_slist_delete(list);
        return 9;
    }
    static int v1 = 10, v2 = 20, v3 = 30;
    cx_slist_push_back(list, &v1);
    if (cx_slist_size(list) != 1) {
        fprintf(stderr, "after push_back size=%zu (expected 1)\n",
                cx_slist_size(list));
        cx_slist_delete(list);
        return 10;
    }
    cx_slist_push_front(list, &v2);
    if (cx_slist_size(list) != 2) {
        fprintf(stderr, "after push_front size=%zu (expected 2)\n",
                cx_slist_size(list));
        cx_slist_delete(list);
        return 11;
    }
    cx_slist_push_back(list, &v3);
    if (cx_slist_size(list) != 3) {
        fprintf(stderr, "after push_back size=%zu (expected 3)\n",
                cx_slist_size(list));
        cx_slist_delete(list);
        return 12;
    }
    if (cx_slist_front(list) != &v2 || cx_slist_back(list) != &v3) {
        fprintf(stderr, "front/back element access mismatch\n");
        cx_slist_delete(list);
        return 13;
    }

    /* Assertion 5: pop_front shrinks size and advances the front element */
    if (cx_slist_pop_front(list) != &v2) {
        fprintf(stderr, "pop_front did not return v2\n");
        cx_slist_delete(list);
        return 14;
    }
    if (cx_slist_size(list) != 2) {
        fprintf(stderr, "after pop_front size=%zu (expected 2)\n",
                cx_slist_size(list));
        cx_slist_delete(list);
        return 15;
    }
    if (cx_slist_front(list) != &v1) {
        fprintf(stderr, "after pop_front front is not v1\n");
        cx_slist_delete(list);
        return 16;
    }
    cx_slist_pop_front(list);
    cx_slist_pop_front(list);
    if (!cx_slist_empty(list)) {
        fprintf(stderr, "list not empty after draining\n");
        cx_slist_delete(list);
        return 17;
    }
    cx_slist_delete(list);

    puts("libcext api assertions: 5 passed");
    return 0;
}
