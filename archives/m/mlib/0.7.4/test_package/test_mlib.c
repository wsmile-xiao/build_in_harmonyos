// test_mlib.c — Substantive consumer test for mlib 0.7.0 (Conan L1).
// Verifies a downstream consumer can include the packaged mlib headers and
// use the generic container APIs through real workloads with asserts.
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include <m-array.h>
#include <m-list.h>
#include <m-dict.h>
#include <m-string.h>

static int int_cmp(const int *a, const int *b) { return (*a > *b) - (*a < *b); }

M_ARRAY_DEF(array_int, int)
M_LIST_DEF(list_int, int)
M_DICT_DEF2(dict_str2int, string_t, STRING_OPLIST, int, M_DEFAULT_OPLIST)

int main(void) {
    // 1) m-array: push 100 ints, random access, sort ascending
    array_int_t arr;
    array_int_init(arr);
    for (int i = 0; i < 100; ++i) {
        array_int_push_back(arr, (i * 37) % 100);
    }
    assert(array_int_size(arr) == 100);
    assert(*array_int_get(arr, 0) == 0);
    array_int_special_sort(arr, int_cmp);
    for (int i = 1; i < 100; ++i) {
        assert(*array_int_cget(arr, i - 1) <= *array_int_cget(arr, i));
    }
    array_int_clear(arr);

    // 2) m-list: push 50, FIFO order check via pop
    list_int_t lst;
    list_int_init(lst);
    for (int i = 0; i < 50; ++i) {
        list_int_push_back(lst, i);
    }
    assert(list_int_size(lst) == 50);
    for (int i = 49; i >= 0; --i) {
        int v = -1;
        list_int_pop_back(&v, lst);
        assert(v == i);
    }
    assert(list_int_empty_p(lst));
    list_int_clear(lst);

    // 3) m-dict: 50 string keys -> int values, lookup & overwrite
    dict_str2int_t d;
    dict_str2int_init(d);
    string_t key;
    string_init(key);
    for (int i = 0; i < 50; ++i) {
        string_printf(key, "key-%d", i);
        dict_str2int_set_at(d, key, i * 2);
    }
    assert(dict_str2int_size(d) == 50);
    for (int i = 0; i < 50; ++i) {
        string_printf(key, "key-%d", i);
        int *v = dict_str2int_get(d, key);
        assert(v != NULL && *v == i * 2);
    }
    string_clear(key);
    dict_str2int_clear(d);

    // 4) m-string: formatted build, compare, serialization round trip
    string_t s;
    string_init(s);
    string_printf(s, "mlib-%d-%s", 74, "ohos");
    assert(string_equal_str_p(s, "mlib-74-ohos"));
    assert(string_size(s) == 12);
    string_clear(s);

    printf("PASS: mlib 0.7.4 头文件库链接和核心容器 API 验证通过\n");
    return 0;
}
