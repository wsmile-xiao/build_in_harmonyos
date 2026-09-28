/*
 * samba 4.21.0 消费者用例：调用 libwbclient 公开 API。
 * 使用包内安装的公开头 wbclient.h：
 *  - wbcStringToSid / wbcSidToString：SID 字符串 <-> 二进制互转；
 *  - wbcFreeMemory：释放 wbcSidToString 分配的内存。
 * 纯字符串解析，无需 winbindd 守护进程。编译、链接、运行三步验证。
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "wbclient.h"

int main(void)
{
    struct wbcDomainSid sid;
    char *sid_string = NULL;

    if (!WBC_ERROR_IS_OK(wbcStringToSid("S-1-5-21-1111111111-2222222222-3333333333-1001", &sid))) {
        printf("FAIL wbcStringToSid\n");
        return 1;
    }
    if (sid.sid_rev_num != 1 || sid.num_auths != 5) {
        printf("FAIL SID fields\n");
        return 2;
    }
    if (!WBC_ERROR_IS_OK(wbcSidToString(&sid, &sid_string))) {
        printf("FAIL wbcSidToString\n");
        return 3;
    }
    if (strcmp(sid_string, "S-1-5-21-1111111111-2222222222-3333333333-1001") != 0) {
        printf("FAIL SID roundtrip mismatch: %s\n", sid_string);
        return 4;
    }

    printf("wbclient_sid_roundtrip_ok v%s\n", sid_string);
    wbcFreeMemory(sid_string);
    return 0;
}
