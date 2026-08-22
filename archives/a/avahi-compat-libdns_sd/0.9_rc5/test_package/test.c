/*
 * test.c — avahi-compat-libdns_sd 消费者测试（真实调用 libdns_sd API）。
 *
 * 覆盖：
 *   1. TXTRecord* 系列（txt.c 实现，纯计算，无需 avahi 守护进程）
 *   2. DNSServiceRegister 非法 regtype 输入校验（compat.c 实现，
 *      与上游 null-test 相同的断言路径，无需守护进程）
 *
 * 测试结束后输出 HMBS_TEST_PACKAGE_RESULT 标记，数字来自实际断言计数。
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <avahi-compat-libdns_sd/dns_sd.h>

#define MAX_CHECKS 12

static int g_checks = 0;
static int g_passed = 0;

static void check(int cond, const char *what) {
    g_checks++;
    if (cond) {
        g_passed++;
    } else {
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

int main(void) {
    TXTRecordRef ref;
    const void *ptr;
    uint8_t val_len = 0;
    DNSServiceRef sdref = NULL;

    /* ── TXTRecord API（txt.c） ── */
    TXTRecordCreate(&ref, 0, NULL);
    check(TXTRecordGetLength(&ref) == 0, "TXTRecordGetLength empty");

    check(TXTRecordSetValue(&ref, "foo", 3, "bar") == kDNSServiceErr_NoError,
          "TXTRecordSetValue foo");
    check(TXTRecordContainsKey(TXTRecordGetLength(&ref),
                               TXTRecordGetBytesPtr(&ref), "foo") == 1,
          "TXTRecordContainsKey foo");

    ptr = TXTRecordGetValuePtr(TXTRecordGetLength(&ref),
                               TXTRecordGetBytesPtr(&ref), "foo", &val_len);
    check(ptr != NULL && val_len == 3 && memcmp(ptr, "bar", 3) == 0,
          "TXTRecordGetValuePtr foo=bar");

    check(!TXTRecordContainsKey(TXTRecordGetLength(&ref),
                                TXTRecordGetBytesPtr(&ref), "nope"),
          "TXTRecordContainsKey nope false");

    check(TXTRecordRemoveValue(&ref, "foo") == kDNSServiceErr_NoError,
          "TXTRecordRemoveValue foo");
    check(!TXTRecordContainsKey(TXTRecordGetLength(&ref),
                                TXTRecordGetBytesPtr(&ref), "foo"),
          "TXTRecordContainsKey foo after remove");
    TXTRecordDeallocate(&ref);

    /* ── DNSService* 输入校验（compat.c，无需守护进程） ── */
    /* 非法 regtype 必须返回错误且不产生引用（与上游 null-test 一致） */
    check(DNSServiceRegister(&sdref, 0, 0, "x", "", NULL, NULL, 4711, 0,
                             NULL, NULL, NULL) != kDNSServiceErr_NoError,
          "DNSServiceRegister empty regtype errors");
    check(sdref == NULL, "DNSServiceRegister empty regtype keeps ref NULL");

    check(DNSServiceRegister(&sdref, 0, 0, "x", ",", NULL, NULL, 4711, 0,
                             NULL, NULL, NULL) != kDNSServiceErr_NoError,
          "DNSServiceRegister ',' regtype errors");
    check(sdref == NULL, "DNSServiceRegister ',' keeps ref NULL");

    /* 空引用释放必须安全（无守护进程场景） */
    DNSServiceRefDeallocate(NULL);
    check(1, "DNSServiceRefDeallocate(NULL) safe");

    /* ── 结果标记（hmbs 机器证据） ── */
    {
        int ok = (g_passed == g_checks && g_checks > 0) ? 1 : 0;
        printf("HMBS_TEST_PACKAGE_RESULT="
               "{\"executed\":true,\"passed\":%s,"
               "\"command\":\"test_dns_sd\","
               "\"discovered\":%d,\"passedCount\":%d}\n",
               ok ? "true" : "false", g_checks, g_passed);
        fflush(stdout);
        return ok ? 0 : 1;
    }
}
