#include <zlib.h>
#include <stdio.h>

/* 消费者视角验证：真实调用 zlib API（R34）。 */
int main(void) {
    printf("zlib %s ok\n", zlibVersion());
    return 0;
}
