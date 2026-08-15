// test_package/test.cpp — dbg-macro 消费者测试
// 验证可包含 dbg.h 并调用 dbg() 宏。
#include <dbg.h>
#include <cstdio>

int main() {
    int x = 42;
    // dbg() 宏：打印表达式 + 值，返回表达式的值
    int y = dbg(x);

    if (y != 42) {
        fprintf(stderr, "FAIL: dbg() did not return the value (got %d)\n", y);
        return 1;
    }

    // 复杂表达式
    auto r = dbg(1 + 2 * 3);
    if (r != 7) {
        fprintf(stderr, "FAIL: dbg expression mismatch (got %d)\n", r);
        return 1;
    }

    printf("dbg-macro smoke test: PASS (dbg() works)\n");
    return 0;
}
