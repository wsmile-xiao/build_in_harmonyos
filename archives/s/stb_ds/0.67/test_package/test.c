/* test.c — 消费者测试：实质调用 stb_ds API（动态数组 + 哈希表） */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define STB_DS_IMPLEMENTATION
#include "stb_ds.h"

int main(void) {
    /* 动态数组 */
    int *arr = NULL;
    arrput(arr, 1);
    arrput(arr, 2);
    arrput(arr, 3);
    assert(arrlen(arr) == 3);
    assert(arr[0] == 1 && arr[1] == 2 && arr[2] == 3);
    arrfree(arr);

    /* 哈希表 (int key -> int value)：元素须为含 key/value 字段的结构体 */
    struct { int key, value; } *map = NULL;
    hmput(map, 42, 7);
    hmput(map, 100, 200);
    assert(hmlen(map) == 2);
    assert(hmget(map, 42) == 7);
    assert(hmget(map, 100) == 200);
    hmfree(map);

    /* 字符串哈希表 (char* key -> int value) */
    struct { char *key; int value; } *smap = NULL;
    shput(smap, "hello", 1);
    shput(smap, "world", 2);
    assert(shlen(smap) == 2);
    assert(shget(smap, "hello") == 1);
    assert(shget(smap, "world") == 2);
    shfree(smap);

    printf("test stb_ds 0.67: OK\n");
    return 0;
}
