#include <features.h>

/* 消费者视角：验证安装后的 uClibc 头文件可用（R34）。
 * 仅编译（-c），不链接不运行：作为 libc 本体，链接属 freestanding 场景。 */
int main(void) {
#ifdef __UCLIBC__
    return (__UCLIBC_MAJOR__ << 16) | (__UCLIBC_MINOR__ << 8) | __UCLIBC_SUBLEVEL__;
#else
#error "not compiled against uClibc headers (__UCLIBC__ undefined)"
#endif
}
