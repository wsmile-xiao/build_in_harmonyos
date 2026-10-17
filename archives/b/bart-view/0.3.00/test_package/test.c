/* test_package/test.c — bart-view 0.3.00 consumer test (L0c 载体)
 *
 * bart-view 是应用型包（交付 view / cfl2png 两个 CLI，无库 API），消费者
 * 验证以实际执行被测二进制为准（见 conanfile.py test() 与
 * test_cfl2png.py）。本文件为 L0c 测试源文件载体，由 test_package 构建。
 */
#include <stdio.h>

int main(void) {
    printf("bart-view 0.3.00 consumer test (application-level)\n");
    return 0;
}
