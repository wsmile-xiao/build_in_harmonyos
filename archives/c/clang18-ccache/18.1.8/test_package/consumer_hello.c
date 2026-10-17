/* 消费者用例：模拟业务上层组件使用 clang18-ccache 提供的 ccache 编译器
   包装器（公开 CLI 接口，R34 实质消费），编译本源文件并通过缓存命中
   验证缓存功能。本程序自身是真实 C 源，可编译、可链接、可运行。 */
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    int a = 1, b = 2;
    if (argc > 2) {
        a = atoi(argv[1]);
        b = atoi(argv[2]);
    }
    printf("consumer-ohos-hello: clang18-ccache works, sum=%d\n", a + b);
    return 0;
}
