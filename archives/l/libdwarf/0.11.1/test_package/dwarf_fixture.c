/*
 * dwarf_fixture.c — 真实本地 ELF/DWARF fixture
 *
 * 由 test_package/CMakeLists.txt 以 -g 编译为带 DWARF 调试信息的 ELF
 * 可执行文件（不 strip），供 test_package 通过 dwarf_init_path() 打开，
 * 遍历真实 compilation unit、获取有效 Dwarf_Die、调用 dwarf_attrlist()
 * 做真实 DWARF 查询验证。
 *
 * 本文件自身行为无关紧要（作为可执行程序返回 0），关键是其 DWARF 调试段
 * 内容（变量/函数/行号/结构体）是真实可解析的。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct record {
    const char *name;
    int         id;
    double      weight;
};

static int helper_add(int a, int b) {
    int sum = a + b;   /* local var, should appear in DWARF */
    return sum;
}

static double helper_scale(struct record *r, double factor) {
    double scaled = (double)r->id * factor;
    return scaled;
}

int main(int argc, char **argv) {
    struct record rec;
    int local_value = 0;
    int i;

    rec.name = "fixture";
    rec.id = 42;
    rec.weight = 3.14;

    for (i = 0; i < argc; ++i) {
        local_value += helper_add(i, 1);
    }
    local_value += (int)helper_scale(&rec, 2.0);

    printf("dwarf_fixture: argc=%d local_value=%d name=%s\n",
           argc, local_value, rec.name);
    return EXIT_SUCCESS;
}
