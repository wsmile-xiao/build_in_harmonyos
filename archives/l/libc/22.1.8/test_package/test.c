/* test_package/test.c — 用包内 LLVM libc 编译链接并运行的 C 程序（R34 反空壳）
 *
 * 验证 LLVM libc 的核心字符串/内存 API（strlen / memcmp / memcpy）真实可用：
 * 这些函数是 C 标准库最底层的部分，链接到包内 libc.a，运行返回码区分各项断言。
 */
#include <string.h>

int main(void) {
    const char *s = "hello llvm-libc";
    char buf[16];

    /* 1) strlen 计算字符串长度（期望 15） */
    if (strlen(s) != 15) {
        return 1;
    }

    /* 2) memcmp 逐字节比较（前 5 字节 "hello"） */
    if (memcmp(s, "hello", 5) != 0) {
        return 2;
    }

    /* 3) memcpy 复制 6 字节（含 NUL），再校验首字节 */
    memcpy(buf, "probe!", 7);
    if (buf[0] != 'p' || buf[5] != '!') {
        return 3;
    }

    return 0;
}
