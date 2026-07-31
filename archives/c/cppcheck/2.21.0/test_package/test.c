/* test.c — 验证 cppcheck 静态分析功能 */
#include <stdio.h>

int main(void) {
    int x;           /* 未使用变量，cppcheck 应报 style:unusedVariable */
    printf("hello\n");
    return 0;
}
