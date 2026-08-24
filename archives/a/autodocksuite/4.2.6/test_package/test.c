/* test_package/test.c — autodocksuite 4.2.6 consumer test
 *
 * autodock/autogrid 是 CLI 程序（无链接库 API），消费者验证聚焦可执行：
 * autodock --help / autogrid 输出（由 conanfile.py test() 运行）。
 * 本 C 文件为 L0c 测试源文件载体。
 */
#include <stdio.h>

int main(void) {
    printf("autodocksuite 4.2.6 consumer test (application-level)\n");
    return 0;
}
