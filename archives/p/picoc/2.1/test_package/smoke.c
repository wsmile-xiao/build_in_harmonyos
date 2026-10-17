/* picoc 2.1 — test_package 冒烟程序（真实 picoc 语言程序）
 * 文件模式运行：picoc smoke.c（picoc 语义要求 main() 入口，stdio 需显式 include） */
#include <stdio.h>

int main()
{
    int answer = 6 * 7;
    if (answer != 42)
        return 1;
    printf("picoc-test-ok %d\n", answer);
    return 0;
}
