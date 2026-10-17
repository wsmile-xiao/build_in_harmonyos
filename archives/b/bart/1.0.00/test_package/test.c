/* test_package/test.c — bart 1.0.00 consumer test
 *
 * bart 是 CLI 程序（无链接库 API），消费者验证聚焦可执行：
 * bart version 输出版本信息（由 conanfile.py test() 运行）。
 * 本 C 文件为 L0c 测试源文件载体。
 */
#include <stdio.h>

int main(void) {
    printf("bart 1.0.00 consumer test (application-level)\n");
    return 0;
}
