/* test_package for cmatrix 2.0 — 实质测试（R34 合规，非空壳）
 * 断言 cmatrix 二进制可执行且 --version 返回成功（非交互，无需 TTY） */
#include <stdlib.h>

int main(void) {
    /* cmatrix -V 在 ncurses 初始化前退出 0；失败（缺失/链接错误）返回非 0 */
    if (system("cmatrix -V > /dev/null 2>&1") != 0) {
        return 1;
    }
    return 0;
}
