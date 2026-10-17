/*
 * test_package/upstream_test.c — SCWS 1.2.3 上游测试用例复刻 (17 项)
 *
 * 来源: 上游源码包 phpext/scws_test.php 的 $TEST_DATA（官方自动测试脚本，
 * 该文件不在 `make check` 内，需 PHP 扩展运行；本仓库不引入 PHP 工具链，
 * 因此以 libscws C API 逐条复刻同样的输入/选项/期望输出）。
 *
 * 上游 17 条用例的选项编码沿用 scws_test.php:
 *   bit0 SCWS_TEST_MULTI_SHORT   -> SCWS_MULTI_SHORT
 *   bit1 SCWS_TEST_MULTI_DUALITY -> SCWS_MULTI_DUALITY
 *   bit2 SCWS_TEST_MULTI_ZMAIN   -> SCWS_MULTI_ZMAIN
 *   bit3 SCWS_TEST_MULTI_ZALL    -> SCWS_MULTI_ZALL
 *   bit4 SCWS_TEST_IGNORE_SYMBOL -> scws_set_ignore(1)
 *   bit5 SCWS_TEST_DUALITY       -> scws_set_duality(1)
 * （PHP 扩展把 multi 值 <<12 传给 scws_set_multi，与 CLI -M 同构）
 *
 * 词典: 官方 scws-dict-chs-utf8.tar.bz2 的 dict.utf8.xdb（与上游 PHP 测试
 * 使用的 ini_get('scws.default.fpath') . '/dict.utf8.xdb' 同一发布件）；
 * 规则: 包内 etc/rules.utf8.ini。
 * 构建需开启 --enable-namerule（人名/路名识别），否则「马明练」「李姚明」
 * 等用例的期望结果无法达成。
 *
 * 计数口径: 每条用例 = 1 项，共 17 项。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <scws/scws.h>
#include <scws/xdict.h>

#define CASE_MULTI_SHORT   0x01
#define CASE_MULTI_DUALITY 0x02
#define CASE_MULTI_ZMAIN   0x04
#define CASE_MULTI_ZALL    0x08
#define CASE_MULTI_MASK    0x0f
#define CASE_IGNORE_SYMBOL 0x10
#define CASE_DUALITY       0x20

struct test_case
{
    int opt;
    const char *text;
    const char *expect;
};

static const struct test_case cases[] = {
    { 0x00,  "大家好，我是马明练",
      "大家 好 ， 我 是 马明练" },
    { 0x00,  "结合成分子时",
      "结合 成 分子 时" },
    { 0x00,  "上海欣辰文化传播有限公司",
      "上海 欣 辰 文化传播 有限公司" },
    { 0x00,  "提高人民生活水平",
      "提高 人民 生活 水平" },
    { 0x00,  "奥巴马上台后中美关系如何变革",
      "奥巴马 上台 后 中美关系 如何 变革" },
    { 0x00,  "一九四九年，新中国成立了",
      "一九四九年 ， 新中国 成立 了" },
    { 0x00,  "哪个人生下来就会算算术呢",
      "哪个 人 生下 来 就 会 算 算术 呢" },
    { 0x00,  "2008年中国网络游戏的实际销售收入达183.8亿元人民币，比2007年增长了76.6%",
      "2008 年 中国 网络游戏 的 实际 销售 收入 达 183.8 亿 元 人民币 ， 比 2007 年 增长 了 76.6%" },
    { 0x00,  "你说的确实在理",
      "你 说 的 确实 在理" },
    { 0x10,  "圆周率的近似值为3.14！",
      "圆周率 的 近似值 为 3.14" },
    { 0x05,  "中国的全称是中华人民共和国",
      "中国 国 的 全称 称 是 中华人民共和国 中华 人民 共和国 华 人 民 国" },
    { 0x30,  "读到第三章，我也不知该说什么好了",
      "读到 到 第三章 我也 也 不知 该 该说 说 什么 好 好了" },
    { 0x02,  "我家的IP是192.168.1.100，4年前就用了，型号是386AC90F",
      "我家 的 IP 是 192 . 168 . 1 . 100 ， 4 年前 就 用 了 ， 型号 是 386 AC 90 90F" },
    { 0x03,  "管理制度，越南民主共和国",
      "管理制度 管理 制度 ， 越南民主共和国 越南 民主 共和国" },
    { 0x03,  "李姚明",
      "李姚明 李姚 姚明" },
    { 0x01,  "李姚明",
      "李姚明" },
    { 0x03,  "中华人民共和国",
      "中华人民共和国 中华 人民 共和国" },
};

#define NCASES ((int) (sizeof(cases) / sizeof(cases[0])))

static int g_fail = 0;

/* 复刻 scws_test.php: 分词结果以空格连接并逐条比对 */
static const char *segment(scws_t s, const char *text, char *buf, size_t buflen)
{
    scws_res_t res, cur;
    size_t pos = 0;

    buf[0] = '\0';
    scws_send_text(s, text, (int) strlen(text));
    /* scws_get_result() hands out tokens in batches (one batch per call):
     * keep calling it until it returns NULL, exactly like the upstream PHP
     * test's `while ($result = $scws->get_result())` loop. */
    while ((res = scws_get_result(s)) != NULL)
    {
        for (cur = res; cur != NULL; cur = cur->next)
        {
            int n;
            if (pos > 0 && pos + 1 < buflen)
                buf[pos++] = ' ';
            n = snprintf(buf + pos, buflen - pos, "%.*s", (int) cur->len,
                         text + cur->off);
            if (n < 0 || (size_t) n >= buflen - pos)
            {
                pos = buflen - 1;
                break;
            }
            pos += (size_t) n;
        }
        scws_free_result(res);
        if (pos >= buflen - 1)
            break;
    }
    return buf;
}

int main(int argc, char **argv)
{
    const char *dict = (argc > 1) ? argv[1] : NULL;
    const char *rule = (argc > 2) ? argv[2] : NULL;
    scws_t s;
    char got[4096];
    int i, pass = 0;

    if (dict == NULL)
    {
        printf("[FAIL] usage: upstream_test <dict.utf8.xdb> <rules.utf8.ini>\n");
        return 1;
    }

    printf("=== scws 1.2.3 upstream test cases (phpext/scws_test.php) ===\n");
    printf("dict: %s\nrule: %s\n", dict, rule ? rule : "(none)");

    s = scws_new();
    if (s == NULL)
    {
        printf("[FAIL] scws_new() failed\n");
        return 1;
    }
    scws_set_charset(s, "utf8");
    if (scws_set_dict(s, dict, SCWS_XDICT_XDB) != 0)
    {
        printf("[FAIL] scws_set_dict(%s) failed\n", dict);
        scws_free(s);
        return 1;
    }
    if (rule != NULL)
        scws_set_rule(s, rule);

    for (i = 0; i < NCASES; i++)
    {
        const char *expect = cases[i].expect;
        scws_set_multi(s, (cases[i].opt & CASE_MULTI_MASK) << 12);
        scws_set_ignore(s, (cases[i].opt & CASE_IGNORE_SYMBOL) ? 1 : 0);
        scws_set_duality(s, (cases[i].opt & CASE_DUALITY) ? 1 : 0);
        segment(s, cases[i].text, got, sizeof(got));
        if (strcmp(got, expect) == 0)
        {
            pass++;
            printf("[PASS] upstream case %02d opt=0x%02x %s\n",
                   i + 1, cases[i].opt, cases[i].text);
        }
        else
        {
            g_fail++;
            printf("[FAIL] upstream case %02d opt=0x%02x %s\n"
                   "       expect: %s\n       actual: %s\n",
                   i + 1, cases[i].opt, cases[i].text, expect, got);
        }
    }
    scws_free(s);

    printf("--- upstream cases: %d/%d passed ---\n", pass, NCASES);
    return (g_fail == 0) ? 0 : 1;
}
