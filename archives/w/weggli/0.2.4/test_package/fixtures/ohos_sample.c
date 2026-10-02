/* HarmonyOS PC sample fixture for the weggli consumer test.
 *
 * 目标三元组 aarch64-unknown-linux-ohos（OHOS PC / armv8）。
 * 函数名与符号名带 OHOS 前缀，便于 H3 用例做鸿蒙专属语义查询断言。
 */
#include <string.h>

extern int OHOS_PC_UPSTREAM_sample(int len);

int copy_ohos_payload(const char *src, unsigned len) {
    char buf[64];
    if (len > 64) {
        return -1;
    }
    memcpy(buf, src, len);
    return OHOS_PC_UPSTREAM_sample(len);
}
