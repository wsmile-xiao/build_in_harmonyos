/* test.c — L1 test for cffi/0.24.1
 *
 *实质依赖被测包: 调用 cffi tests/libtest.so 中导出的函数和变量,
 *验证 build() 编译的测试共享库有效, 且 C FFI 机制可正常工作。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* libtest.so 导出符号 (extern 声明) */
extern char *my_strdup(const char *str);
extern void my_strfree(char *str);
extern char *dll_version;
extern int var_int;
extern double var_double;

int main(void) {
    /* 1. 调用导出函数 my_strdup */
    char *s = my_strdup("cffi-test");
    if (s == NULL) {
        fprintf(stderr, "FAIL: my_strdup returned NULL\n");
        return 1;
    }
    if (strcmp(s, "cffi-test") != 0) {
        fprintf(stderr, "FAIL: my_strdup content mismatch: %s\n", s);
        my_strfree(s);
        return 1;
    }
    my_strfree(s);
    printf("OK: my_strdup/my_strfree work\n");

    /* 2. 读导出变量 dll_version (期望 "20120107") */
    if (dll_version == NULL || strcmp(dll_version, "20120107") != 0) {
        fprintf(stderr, "FAIL: dll_version mismatch: %s\n", dll_version ? dll_version : "(null)");
        return 1;
    }
    printf("OK: dll_version = %s\n", dll_version);

    /* 3. 读导出变量 var_int (期望 -32767) */
    if (var_int != -32767) {
        fprintf(stderr, "FAIL: var_int mismatch: %d\n", var_int);
        return 1;
    }
    printf("OK: var_int = %d\n", var_int);

    /* 4. 读导出变量 var_double (期望 42.0) */
    if (var_double != 42.0) {
        fprintf(stderr, "FAIL: var_double mismatch: %f\n", var_double);
        return 1;
    }
    printf("OK: var_double = %f\n", var_double);

    printf("cffi L1 test PASSED\n");
    return 0;
}
