#include <stdio.h>
#if !defined(__clang__)
#error "not compiled by clang"
#endif
/* R34 反空壳：证明被测包（clang 20.1.8）真实参与编译——编译器必须报告 clang 20.x */
#if __clang_major__ != 20
#error "unexpected clang major version"
#endif
int main(void) {
    printf("clang %d.%d.%d ok\n", __clang_major__, __clang_minor__, __clang_patchlevel__);
    return 0;
}
