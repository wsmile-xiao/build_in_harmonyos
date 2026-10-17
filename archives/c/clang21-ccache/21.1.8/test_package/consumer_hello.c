/* 消费者用例：模拟业务上层使用 clang21-ccache 提供的 ccache 编译器包装器，
   编译一个真实 C 程序并验证其可运行输出（公开 CLI 接口，R34 实质消费）。 */
#include <stdio.h>

int main(void) {
    printf("consumer-ohos-hello: clang21-ccache works, sum=%d\n", 1 + 2);
    return 0;
}
