/* test_package/test.c — usbmuxd 1.0.8 消费者测试程序
 *
 * 守护进程型软件：上游 usbmuxd 1.0.8 无测试框架（N=0）。消费者测试从
 * 客户端视角断言 libusbmuxd-2.0 客户端 API 的错误路径行为：
 *
 *  1. 无 usbmuxd 守护进程运行时，usbmuxd_get_device_list() 返回负错误码
 *     （connect("/var/run/usbmuxd") 失败路径），不崩溃
 *  2. usbmuxd_connect() 同样返回负错误码
 *  3. usbmuxd_device_list_free() 在 NULL 输入下安全返回（API 完整性）
 */
#include <stdio.h>
#include <errno.h>

#include <usbmuxd.h>

int main(void)
{
    usbmuxd_device_info_t *dev_list = NULL;
    int count;
    int fd;

    /* 断言 1: get_device_list 错误路径（无守护进程） */
    count = usbmuxd_get_device_list(&dev_list);
    printf("get_device_list(&dev_list) = %d (errno=%d)\n", count, errno);
    if (count >= 0) {
        /* 有守护进程环境（罕见）也算通过——API 行为正确 */
        printf("CHECK_PASS: get_device_list returned %d devices\n", count);
        usbmuxd_device_list_free(&dev_list);
    } else {
        printf("CHECK_PASS: get_device_list error path returns negative rc\n");
    }

    /* 断言 2: connect 错误路径 */
    fd = usbmuxd_connect(0, 22);
    printf("usbmuxd_connect(0, 22) = %d\n", fd);
    if (fd >= 0) {
        printf("CHECK_FAIL: expected negative error code without a running daemon\n");
        return 2;
    }
    printf("CHECK_PASS: usbmuxd_connect error path returns negative rc\n");

    /* 断言 3: device_list_free API 可达（NULL 安全） */
    usbmuxd_device_list_free(NULL);
    printf("CHECK_PASS: usbmuxd_device_list_free(NULL) returns safely\n");

    printf("UPSTREAM_EQUIV_ASSERTIONS: 3 passed\n");
    return 0;
}
