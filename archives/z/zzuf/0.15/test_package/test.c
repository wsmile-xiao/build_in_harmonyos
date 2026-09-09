/*
 * test_zzuf_victim.c — zzuf 0.15 消费者验证受害者程序
 *
 * 从 stdin 读取字节并原样写回 stdout（迷你 cat）。
 * 由 test_package/conanfile.py 的 test() 编译后，在 zzuf 驱动下运行：
 * 被 libzzuf.so 拦截时输出会被按比率翻转（与原始输入不同且确定性可复现），
 * 从而端到端验证 OHOS 上 LD_PRELOAD 拦截链路真实生效（R34 实质调用被测包）。
 */
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int c;
    unsigned long total = 0;
    while ((c = getchar()) != EOF)
    {
        putchar(c);
        total++;
    }
    if (ferror(stdin))
    {
        fprintf(stderr, "test_zzuf_victim: read error\n");
        return 1;
    }
    fprintf(stderr, "test_zzuf_victim: %lu bytes\n", total);
    return 0;
}