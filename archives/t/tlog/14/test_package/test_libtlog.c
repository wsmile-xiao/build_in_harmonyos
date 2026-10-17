/*
 * libtlog 消费者侧测试（tlog 14 / HarmonyOS OHOS aarch64）。
 *
 * 全部断言走真实 API 调用，共 18 条，分四族：
 *   1. grc     —— 错误码构造 / 判族 / 往返 / 字符串化（tlog 全库的错误处理基石）
 *   2. utf8    —— 录制日志的用户名/命令行走 UTF-8 校验（rec.c:722 用到）
 *   3. timestr —— 时间戳字符串 <-> **struct timespec**（补丁 0004-0010 补的
 *                 POSIX 类型之一；能编译通过即证明补丁生效）
 *   4. pkt     —— 录制包对象的生命周期（void/io 初始化、有效性、相等、清理）
 *
 * 返回 0 表示全部通过，非 0 表示有断言失败（失败条数打印在 stderr）。
 */
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include <tlog/grc.h>
#include <tlog/pkt.h>
#include <tlog/rc.h>
#include <tlog/timestr.h>
#include <tlog/utf8.h>

static unsigned int g_passed = 0;
static unsigned int g_failed = 0;

#define CHECK(_cond, _what)                     \
    do {                                        \
        if (_cond) {                            \
            g_passed++;                         \
            printf("ok   %s\n", (_what));       \
        } else {                                \
            g_failed++;                         \
            printf("FAIL %s\n", (_what));       \
        }                                       \
    } while (0)

int
main(void)
{
    tlog_grc grc_enoent;
    struct timespec ts;
    struct tlog_pkt pkt;
    const uint8_t payload[] = "hello";

    /* ── 1. grc：错误码族 ── */
    grc_enoent = TLOG_GRC_FROM(errno, ENOENT);
    CHECK(tlog_grc_is_valid(grc_enoent), "grc: TLOG_GRC_FROM(errno, ENOENT) 有效");
    CHECK(tlog_grc_is_valid(TLOG_RC_OK), "grc: TLOG_RC_OK 有效");
    CHECK(TLOG_GRC_IS(errno, grc_enoent), "grc: TLOG_GRC_IS(errno, ...) 命中 errno 族");
    CHECK(TLOG_GRC_TO(errno, grc_enoent) == ENOENT, "grc: TLOG_GRC_TO(errno, ...) 取回 ENOENT");
    CHECK(tlog_grc_to(&tlog_grc_range_errno, grc_enoent) == ENOENT,
          "grc: tlog_grc_to 与 TLOG_GRC_TO 一致");
    CHECK(tlog_grc_strerror(grc_enoent) != NULL
          && tlog_grc_strerror(grc_enoent)[0] != '\0',
          "grc: tlog_grc_strerror 非空");

    /* ── 2. utf8：合法（含中文）与非法序列 ── */
    CHECK(tlog_utf8_str_is_valid("tlog 录制"), "utf8: 合法 UTF-8 串（含中文）被接受");
    CHECK(!tlog_utf8_str_is_valid("\xff\xfe"), "utf8: 非法字节序列 0xFF 0xFE 被拒绝");

    /* ── 3. timestr：时间戳字符串 <-> struct timespec ── */
    ts = (struct timespec){.tv_sec = -1, .tv_nsec = -1};
    CHECK(tlog_timestr_to_timespec("1:02:03.5", &ts), "timestr: 解析 \"1:02:03.5\" 成功");
    CHECK(ts.tv_sec == 3723 && ts.tv_nsec == 500000000,
          "timestr: 值 == 3723s + 500000000ns");
    ts = (struct timespec){.tv_sec = -1, .tv_nsec = -1};
    CHECK(tlog_timestr_to_timespec(" ::. ", &ts), "timestr: 省略分量 \" ::. \" 解析成功");
    CHECK(ts.tv_sec == 0 && ts.tv_nsec == 0, "timestr: 省略分量 == 0s + 0ns");
    CHECK(!tlog_timestr_to_timespec(".1000000000", &ts),
          "timestr: 小数位超 9 位被拒绝");

    /* ── 4. pkt：录制包生命周期 ── */
    tlog_pkt_init(&pkt);
    CHECK(tlog_pkt_is_valid(&pkt) && tlog_pkt_is_void(&pkt),
          "pkt: tlog_pkt_init -> 有效空包");
    ts = (struct timespec){.tv_sec = 7, .tv_nsec = 0};
    tlog_pkt_init_io(&pkt, &ts, &ts, true, (uint8_t *)payload, false,
                     sizeof(payload) - 1);
    CHECK(tlog_pkt_is_valid(&pkt) && !tlog_pkt_is_void(&pkt),
          "pkt: tlog_pkt_init_io -> 有效非空包");
    CHECK(pkt.type == TLOG_PKT_TYPE_IO, "pkt: type == TLOG_PKT_TYPE_IO");
    CHECK(tlog_pkt_is_equal(&pkt, &pkt), "pkt: tlog_pkt_is_equal 自比较相等");
    tlog_pkt_cleanup(&pkt);
    CHECK(tlog_pkt_is_valid(&pkt) && tlog_pkt_is_void(&pkt),
          "pkt: tlog_pkt_cleanup -> 回到有效空包");

    printf("libtlog: %u passed, %u failed\n", g_passed, g_failed);
    if (g_failed != 0) {
        fprintf(stderr, "libtlog: %u assertion(s) FAILED\n", g_failed);
        return 1;
    }
    return 0;
}
