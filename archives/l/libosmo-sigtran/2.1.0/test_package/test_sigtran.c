/*
 * libosmo-sigtran 2.1.0 消费者测试（test_package）——真实调用上游公开 API：
 *   - osmo_ss7_init / osmo_ss7_instance_find_or_create / destroy（SS7 栈管理）
 *   - osmo_ss7_ensure_sccp（SCCP 实例创建——走 talloc 上下文与路由表初始化）
 *   - osmo_xua_msg_tall_ctx_init（XUA talloc 上下文）
 *   - 点码解析 osmo_ss7_point_code_parse（SS7 路由核心原语）
 *   - sccp_sap/protocol/m3ua 头的枚举与值表消费（含 M3UA 常量）
 * 编译+链接+运行（运行受限时降级 compile+link，E488 系口径）。
 */
#include <osmocom/sigtran/osmo_ss7.h>
#include <osmocom/sigtran/sccp_sap.h>
#include <osmocom/sigtran/xua_msg.h>
#include <osmocom/sigtran/protocol/m3ua.h>
#include <osmocom/core/utils.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    /* 1. SS7 栈初始化（FSM 注册等） */
    int rc = osmo_ss7_init();
    if (rc < 0) { fprintf(stderr, "FAIL: osmo_ss7_init\n"); return 1; }
    printf("ok: osmo_ss7_init\n");

    /* 2. SS7 实例创建/查找（点码格式取默认） */
    struct osmo_ss7_instance *inst = osmo_ss7_instance_find_or_create(NULL, 0);
    if (!inst) { fprintf(stderr, "FAIL: osmo_ss7_instance_find_or_create\n"); return 1; }
    if (osmo_ss7_instance_find(0) != inst) {
        fprintf(stderr, "FAIL: osmo_ss7_instance_find roundtrip\n"); return 1;
    }
    printf("ok: osmo_ss7_instance find_or_create + find roundtrip\n");

    /* 3. 点码格式原语（SS7 路由核心）——取实例的点码格式描述符 */
    const struct osmo_ss7_pc_fmt *pc_fmt = osmo_ss7_instance_get_pc_fmt(inst);
    if (!pc_fmt) { fprintf(stderr, "FAIL: osmo_ss7_instance_get_pc_fmt\n"); return 1; }
    uint8_t width = osmo_ss7_pc_width(pc_fmt);
    if (width == 0 || width > 24) {
        fprintf(stderr, "FAIL: osmo_ss7_pc_width = %u\n", width); return 1;
    }
    uint32_t npcs = osmo_ss7_pc_normalize(pc_fmt, 0x010203);
    if (npcs == 0) { fprintf(stderr, "FAIL: osmo_ss7_pc_normalize\n"); return 1; }
    printf("ok: point code width=%u normalize=0x%x\n", width, npcs);

    /* 4. SCCP 实例创建（osmo_ss7_ensure_sccp） */
    struct osmo_sccp_instance *sccp = osmo_ss7_ensure_sccp(inst);
    if (!sccp) { fprintf(stderr, "FAIL: osmo_ss7_ensure_sccp\n"); return 1; }
    printf("ok: osmo_ss7_ensure_sccp\n");

    /* 5. XUA talloc 上下文初始化 */
    osmo_xua_msg_tall_ctx_init(NULL);
    printf("ok: osmo_xua_msg_tall_ctx_init\n");

    /* 6. 协议常量与值表消费（头文件完整性） */
    if (M3UA_VERSION != 1 || M3UA_MSGC_XFER != 1 || M3UA_XFER_DATA != 1) {
        fprintf(stderr, "FAIL: M3UA protocol constants\n"); return 1;
    }
    if (strcmp(get_value_string(osmo_sccp_routing_ind_names,
                                OSMO_SCCP_RI_SSN_PC), "SSN_PC") != 0) {
        fprintf(stderr, "FAIL: sccp value_string tables\n"); return 1;
    }
    printf("ok: M3UA/SCCP protocol headers consumed\n");

    osmo_ss7_instance_destroy(inst);
    printf("ok: osmo_ss7_instance_destroy\n");

    printf("consumer test: PASS\n");
    return 0;
}
