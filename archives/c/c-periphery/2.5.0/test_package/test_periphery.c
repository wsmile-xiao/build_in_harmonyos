/* c-periphery 消费者验证：version API + serial 错误路径。
 * 全部断言不依赖真实外设硬件（CI/验证环境可复现）。 */
#include <periphery/serial.h>
#include <periphery/version.h>

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(cond, msg)               \
    do {                               \
        if (cond) {                    \
            printf("PASS: %s\n", msg); \
        } else {                       \
            printf("FAIL: %s\n", msg); \
            failures++;                \
        }                              \
    } while (0)

int main(void)
{
    const char *ver = periphery_version();
    printf("periphery_version: %s\n", ver);
    CHECK(strcmp(ver, "v2.5.0") == 0, "periphery_version() == v2.5.0");

    /* 错误路径：serial_t 为不透明句柄，serial_new 分配后 open 不存在的
     * 串口设备必须失败并置错误状态；open 失败只 free 不 close（fd 未打开）。 */
    serial_t *serial = serial_new();
    CHECK(serial != NULL, "serial_new() allocates handle");

    int ret = serial_open(serial, "/dev/periphery_selftest_nonexistent", 115200);
    CHECK(ret != 0, "serial_open(nonexistent) fails as expected");
    CHECK(serial_errno(serial) != 0, "serial_errno set after failed open");
    printf("serial error info: code=%d msg=%s\n",
           serial_errno(serial), serial_errmsg(serial));
    CHECK(serial_errmsg(serial)[0] != '\0', "serial_errmsg non-empty after failed open");

    serial_free(serial);

    if (failures) {
        printf("test_periphery: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("test_periphery: all checks passed\n");
    return 0;
}
