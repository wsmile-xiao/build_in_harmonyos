/*
 * test_package 消费者测试 — tlsh 5.0.0
 *
 * 真实链接被测包导出的 tlsh::tlsh 目标（静态库 libtlsh.a），断言：
 *   1. Tlsh::version() 的版本前缀（tlsh_version.h 由上游 CMake 生成）；
 *   2. 上游 test/simple_unittest.cpp 的已知输入 → 已知 digest：
 *      与上游夹具 Testing/exp/simple_unittest.128.1.EXP 逐字一致；
 *   3. 距离计算（含/不含长度）与同一对象距离为 0；
 *   4. fromTlshStr 往返一致；
 *   5. 不同输入给出不同 digest。
 * 期望常量全部取自上游 exp 夹具，不做任何平台相关的放宽。
 */
#include <cstdio>
#include <cstring>
#include <string>

#include <tlsh/tlsh.h>

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char *what) {
    ++g_checks;
    if (ok) {
        std::printf("ok   - %s\n", what);
    } else {
        ++g_failed;
        std::printf("FAIL - %s\n", what);
    }
}

/* 与上游 simple_unittest.cpp 完全一致的构造：先 i%26+'A' 铺满，再覆盖前缀 */
static void fill(char *buf, int n, const char *prefix) {
    int len = (int) std::strlen(prefix);
    for (int i = 0; i < n - 1; ++i) {
        buf[i] = (char) (i % 26 + 'A');
    }
    buf[n - 1] = 0;
    std::strncpy(buf, prefix, len);
}

int main() {
    /* 1) 产物自报版本 */
    const char *ver = Tlsh::version();
    std::string version(ver ? ver : "");
    check(!version.empty(), "Tlsh::version() 非空");
    check(version.rfind("5.0.0", 0) == 0, "Tlsh::version() 以 5.0.0 开头");

    /* 2) 上游已知输入 → 已知指纹（Testing/exp/simple_unittest.128.1.EXP） */
    static const char *kStr1 =
        "This is a test for Lili Diao. This is a string. Hello Hello Hello ";
    static const char *kStr2 =
        "This is a test for Jon Oliver. This is a string. Hello Hello Hello ";
    static const char *kHash1 =
        "T109F05A198CC69A5A4F0F9380A9EE93F2B927CF42089EA74276DC5F0BB2D34E68114448";
    static const char *kHash2 =
        "T1301124198C869A5A4F0F9380A9AE92F2B9278F42089EA34272885F0FB2D34E6911444C";

    char buf1[512];
    char buf2[1024];
    fill(buf1, 512, kStr1);
    fill(buf2, 1024, kStr2);

    Tlsh t1;
    Tlsh t2;
    t1.final((const unsigned char *) buf1, 512);
    t2.final((const unsigned char *) buf2, 1024);
    check(t1.isValid(), "t1.isValid()");
    check(t2.isValid(), "t2.isValid()");

    std::string h1(t1.getHash(1));
    std::string h2(t2.getHash(1));
    check(h1.size() == (std::size_t) TLSH_STRING_LEN_REQ,
          "digest 长度 == TLSH_STRING_LEN_REQ");
    check(h1.rfind("T1", 0) == 0, "digest 带 T1 版本前缀（5.0.0 默认行为）");
    check(h1 == kHash1, "t1 指纹与上游 simple_unittest 期望逐字一致");
    check(h2 == kHash2, "t2 指纹与上游 simple_unittest 期望逐字一致");

    /* 3) 距离计算 */
    check(t1.totalDiff(&t1) == 0, "同一对象距离为 0");
    check(t1.totalDiff(&t2) == 121, "t1/t2 含长度距离 == 121");
    check(t1.totalDiff(&t2, false) == 97, "t1/t2 不含长度距离 == 97");

    /* 4) fromTlshStr 往返 */
    Tlsh t3;
    check(t3.fromTlshStr(h1.c_str()) == 0, "fromTlshStr 接受 T1 digest");
    check(t3.isValid(), "fromTlshStr 后 isValid()");
    std::string h3(t3.getHash(1));
    check(h3 == h1, "fromTlshStr 往返 digest 一致");
    check(t3.totalDiff(&t1) == 0, "往返对象与原对象距离为 0");

    /* 5) 不同输入必须给出不同 digest */
    char buf3[512];
    fill(buf3, 512, kStr2);
    Tlsh t4;
    t4.final((const unsigned char *) buf3, 512);
    std::string h4(t4.getHash(1));
    check(h4 != h1, "不同输入 digest 不同");

    std::printf("checks=%d failed=%d\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
