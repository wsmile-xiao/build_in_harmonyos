/*
 * lwbtn 1.3.2 — HarmonyOS consumer end-to-end test (赛事规则12: 鸿蒙特有测试)
 *
 * 独立消费者端到端用例（test_package 之外的完整流程用例）:
 *   - 使用 lwbtn 1.3.2 公开 API (lwbtn_init / lwbtn_process / 事件回调)
 *   - 以真实按压/释放时序驱动按钮状态机, 完成"点击事件判定"流程闭环
 *   - 断言同时包含"事件应当发生"与"事件不应当发生"两类可观察结果,
 *     实现/驱动被破坏时用例会真实失败 (非恒绿)
 *
 * lwbtn 驱动语义 (本库事实): lwbtn_process(mstime) 接收绝对毫秒时间戳;
 * 首次观察到的按钮状态必须为 inactive (LWBTN_FLAG_FIRST_INACTIVE_RCVD)。
 * 默认时序 (lwbtn_opt.h): DEBOUNCE_PRESS=20, DEBOUNCE_RELEASE=0,
 * CLICK_MIN=20, CLICK_MAX=300, CLICK_MULTI_MAX=400。
 *
 * 无平台条件编译宏: 全部走标准 C 单一路径。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "lwbtn/lwbtn.h"

/* 可观察事件计数 (事件回调中累加) */
static unsigned g_onpress = 0;
static unsigned g_onrelease = 0;
static unsigned g_onclick = 0;
static unsigned g_keepalive = 0;

/* 当前按钮输入状态 (驱动用) */
static uint8_t g_btn_state = 0;

static uint8_t
test_get_state(struct lwbtn* lwobj, struct lwbtn_btn* btn) {
    (void)lwobj;
    (void)btn;
    return g_btn_state;
}

static void
test_evt(struct lwbtn* lwobj, struct lwbtn_btn* btn, lwbtn_evt_t evt) {
    (void)lwobj;
    (void)btn;
    switch (evt) {
    case LWBTN_EVT_ONPRESS:
        ++g_onpress;
        break;
    case LWBTN_EVT_ONRELEASE:
        ++g_onrelease;
        break;
    case LWBTN_EVT_ONCLICK:
        ++g_onclick;
        break;
    case LWBTN_EVT_KEEPALIVE:
        ++g_keepalive;
        break;
    default:
        break;
    }
}

/* 重置事件计数与按钮状态 */
static void
test_reset(void) {
    g_onpress = 0;
    g_onrelease = 0;
    g_onclick = 0;
    g_keepalive = 0;
    g_btn_state = 0;
}

/* 从 start_ms 开始, 以 10ms 步进推进状态机, 返回推进到的绝对时刻 */
static unsigned
drive(unsigned start_ms, const char* seq, size_t seq_len) {
    unsigned t = start_ms;
    for (size_t i = 0; i < seq_len; ++i) {
        g_btn_state = (uint8_t)(seq[i] == '1' ? 1 : 0);
        lwbtn_process(t);
        t += 10;
    }
    return t;
}

static int
expect(unsigned actual, unsigned want, const char* what) {
    if (actual == want) {
        printf("PASS: %s = %u\n", what, actual);
        return 0;
    }
    printf("FAIL: %s = %u (expected %u)\n", what, actual, want);
    return 1;
}

int
main(void) {
    lwbtn_btn_t btn;
    unsigned t = 0;
    int rc = 0;

    memset(&btn, 0, sizeof(btn));
    if (lwbtn_init(&btn, 1, test_get_state, test_evt) != 1) {
        printf("FAIL: lwbtn_init returned error\n");
        return 1;
    }

    /*
     * 场景 1 (点击应当发生):
     *   首次 inactive 10ms -> 按压 40ms (>= debounce 20 + click_min 20)
     *   -> 释放 450ms (> click_multi_max 400, 直接上报 click)
     * 期望: 1 次 ONPRESS, 1 次 ONRELEASE, 1 次 ONCLICK
     */
    test_reset();
    drive(t, "0", 1);          /* 首次状态必须 inactive */
    t = drive(10, "1111", 4);  /* 按压 40ms */
    t = drive(t, "000000000000000000000000000000000000000000000", 45); /* 释放 450ms */
    rc |= expect(g_onpress, 1, "场景1 ONPRESS 计数");
    rc |= expect(g_onrelease, 1, "场景1 ONRELEASE 计数");
    rc |= expect(g_onclick, 1, "场景1 ONCLICK 计数(点击应发生)");

    /*
     * 场景 2 (点击不应当发生 - 按压不足):
     *   按压仅 10ms (< debounce 20), 去抖动未通过
     * 期望: 0 次 ONPRESS, 0 次 ONCLICK (事件完全不触发)
     */
    test_reset();
    t = drive(500, "0", 1);
    t = drive(t, "1", 1);      /* 仅 10ms 按压 */
    t = drive(t, "0", 45);     /* 释放 */
    rc |= expect(g_onpress, 0, "场景2 ONPRESS 计数(按压过短不触发)");
    rc |= expect(g_onclick, 0, "场景2 ONCLICK 计数(按压过短不触发)");

    /*
     * 场景 3 (点击不应当发生 - 长按超过 click_max):
     *   按压 500ms (> click_max 300) 为长按而非点击
     * 期望: 有 ONPRESS, 但 0 次 ONCLICK
     */
    test_reset();
    t = drive(1000, "0", 1);
    t = drive(t, "1111111111111111111111111111111111111111111111111", 49); /* 按压 490ms */
    t = drive(t, "0", 45);
    rc |= expect(g_onpress, 1, "场景3 ONPRESS 计数(长按有按压事件)");
    rc |= expect(g_onclick, 0, "场景3 ONCLICK 计数(长按不判为点击)");

    if (rc == 0) {
        printf("lwbtn consumer e2e: ALL PASS (click/长按/时序边界判定闭环)\n");
    } else {
        printf("lwbtn consumer e2e: FAILED (%d assertion(s))\n", rc);
    }
    return rc;
}