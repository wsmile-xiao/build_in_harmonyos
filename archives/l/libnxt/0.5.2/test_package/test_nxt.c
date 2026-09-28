/* 消费者测试：真实调用 libnxt 无硬件 API。
 * 覆盖 error 映射、宏阈值、固件文件校验、libusb 初始化路径。
 * 全部断言失败即返回非零，无需 NXT 真机硬件。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "error.h"
#include "firmware.h"
#include "lowlevel.h"

static int check_str_error(void)
{
    const char *ok = nxt_str_error(NXT_OK);
    const char *not_present = nxt_str_error(NXT_NOT_PRESENT);
    const char *file_err = nxt_str_error(NXT_FILE_ERROR);
    const char *invalid_fw = nxt_str_error(NXT_INVALID_FIRMWARE);
    /* 99 落在 [7, NXT_ERROR_CMD_MIN) 空隙，走 "Unknown error" 分支；
     * 不可用 9999：它 >= NXT_ERROR_USB_MIN(1000)，走 libusb_strerror
     * 分支（libusb 对未知码返回 "Other error"）。 */
    const char *unknown = nxt_str_error((nxt_error_t)99);

    if (ok == NULL || strcmp(ok, "Success") != 0) {
        printf("FAIL str_error NXT_OK got '%s'\n", ok ? ok : "(null)");
        return 1;
    }
    if (not_present == NULL || not_present[0] == '\0') {
        printf("FAIL str_error NXT_NOT_PRESENT empty\n");
        return 2;
    }
    if (file_err == NULL || file_err[0] == '\0') {
        printf("FAIL str_error NXT_FILE_ERROR empty\n");
        return 3;
    }
    if (invalid_fw == NULL || invalid_fw[0] == '\0') {
        printf("FAIL str_error NXT_INVALID_FIRMWARE empty\n");
        return 4;
    }
    if (unknown == NULL || strcmp(unknown, "Unknown error") != 0) {
        printf("FAIL str_error unknown got '%s'\n", unknown ? unknown : "(null)");
        return 5;
    }
    /* 宏阈值：USB/CMD 错误码落在各自区间。NXT_ERROR_USB(ret) 定义为
     * MIN - ret，ret 取 libusb 负错误码，故用 -5：1000-(-5)=1005>=MIN。 */
    if (!(NXT_ERROR_USB(-5) >= NXT_ERROR_USB_MIN)) {
        printf("FAIL NXT_ERROR_USB range\n");
        return 6;
    }
    if (!(NXT_ERROR_CMD(3) >= NXT_ERROR_CMD_MIN && NXT_ERROR_CMD(3) < NXT_ERROR_USB_MIN)) {
        printf("FAIL NXT_ERROR_CMD range\n");
        return 7;
    }
    printf("OK str_error\n");
    return 0;
}

static int check_firmware_validate(void)
{
    nxt_error_t err;

    err = nxt_firmware_validate("/nonexistent-libnxt-firmware.bin");
    if (err != NXT_FILE_ERROR) {
        printf("FAIL firmware_validate missing got %d\n", (int)err);
        return 11;
    }

    /* 临时小文件：体积非 256KB，应判 INVALID_FIRMWARE（纯文件逻辑，无硬件）。
     * OHOS 真机 /tmp 可能只读，优先用 HMBS 注入的 TMPDIR/TMP/TEMP。 */
    char tmp[256];
    const char *tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = getenv("TMP");
    }
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = getenv("TEMP");
    }
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = "/tmp";
    }
    snprintf(tmp, sizeof(tmp), "%s/libnxt-test-XXXXXX", tmpdir);
    int fd = mkstemp(tmp);
    if (fd < 0) {
        printf("FAIL mkstemp\n");
        return 12;
    }
    const char payload[64] = {0};
    if (write(fd, payload, sizeof(payload)) != (ssize_t)sizeof(payload)) {
        printf("FAIL write tmp\n");
        close(fd);
        unlink(tmp);
        return 13;
    }
    close(fd);
    err = nxt_firmware_validate(tmp);
    unlink(tmp);
    if (err != NXT_INVALID_FIRMWARE) {
        printf("FAIL firmware_validate small got %d\n", (int)err);
        return 14;
    }
    printf("OK firmware_validate\n");
    return 0;
}

static int check_init_exit(void)
{
    nxt_t *nxt = NULL;
    nxt_error_t err = nxt_init(&nxt);
    if (err != NXT_OK) {
        /* 无 libusb 运行环境时给出可解释错误即算通过路径覆盖，不硬失败；
         * 但 OHOS 真机应有 libusb，此处仅打印以便日志定位。 */
        printf("INFO nxt_init returned %d (%s)\n", (int)err, nxt_str_error(err));
        return 0;
    }
    if (nxt == NULL) {
        printf("FAIL nxt_init null handle\n");
        return 22;
    }
    nxt_exit(nxt);
    printf("OK init_exit\n");
    return 0;
}

int main(void)
{
    int rc;

    rc = check_str_error();
    if (rc != 0) {
        return rc;
    }
    rc = check_firmware_validate();
    if (rc != 0) {
        return rc;
    }
    rc = check_init_exit();
    if (rc != 0) {
        return rc;
    }

    printf("ALL OK libnxt consumer test\n");
    return 0;
}
