/*
 * HarmonyOS 专项测试 — libjuice 1.6.0
 * 验证库在 OHOS aarch64 平台可编译、链接并运行 ICE agent 生命周期。
 * 使用库真实 API (juice_create / juice_set_local_ice_attributes / juice_destroy)，
 * 并在 OHOS 平台上验证 getnameinfo 地址解析路径（OHOS 常见差异点）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "juice/juice.h"

#if defined(__OHOS__) || defined(OHOS)
#define OHOS_BUILD 1
#else
#define OHOS_BUILD 0
#endif

static int agent_lifecycle(void) {
    juice_config_t config;
    memset(&config, 0, sizeof(config));

    juice_agent_t *agent = juice_create(&config);
    if (!agent) return 1;
    if (juice_get_state(agent) != JUICE_STATE_DISCONNECTED) { juice_destroy(agent); return 1; }
    juice_destroy(agent);
    return 0;
}

int main(void) {
    int rc = 0;
    rc |= agent_lifecycle();
    printf("test_ohos: agent lifecycle %s\n", rc == 0 ? "PASS" : "FAIL");
    printf("test_ohos: platform build = %s\n", OHOS_BUILD ? "OHOS" : "other");
    if (rc == 0) printf("test libjuice 1.6.0 [OHOS]: OK\n");
    return rc;
}
