/* minIni 1.5 完整消费者用例（平台 rule12）
 *
 * 不是断言集合，而是把 minIni 当成真实配置层用一遍并核对结果：
 *   ① 建配置（ini_puts/ini_putl/ini_putbool/ini_putf 写段=键=值）
 *   ② 读回来（ini_gets/ini_getl/ini_getbool/ini_getf）
 *   ③ 默认值语义（缺失键/缺失段）
 *   ④ 存在性判定（ini_haskey/ini_hassection）
 *   ⑤ 枚举：ini_getsection 数段、ini_getkey 数键、ini_browse 全量遍历
 *   ⑥ 更新与删除（覆盖写 + ini_puts(...,NULL,...) 删键）
 *   ⑦ 大小写与注释处理（上游 test.ini 里的尾随注释 / 空格式）
 *
 * 用法: test_minini <工作目录>
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <minIni.h>

static int g_checks = 0;
static int g_failed = 0;

static void check_detail(int ok, const char *what, const char *detail)
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
    }
    printf("  [%s] %s", ok ? "ok" : "FAIL", what);
    if (detail && detail[0]) {
        printf("  %s", detail);
    }
    printf("\n");
}

/* 不带 detail 的简化入口 */
static void check(int ok, const char *what)
{
    check_detail(ok, what, "");
}

static int count_cb(const char *section, const char *key, const char *value, void *userdata)
{
    int *counter = (int *)userdata;
    (void)section;
    (void)key;
    (void)value;
    ++(*counter);
    return 1;   /* 返回 1 继续遍历 */
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <workdir>\n", argv[0]);
        return 2;
    }
    char path[512];
    snprintf(path, sizeof(path), "%s/app.ini", argv[1]);
    remove(path);
    char detail[160];

    printf("minIni 消费者用例：真实配置读写流程\n");

    /* ① 建配置 */
    int ok = ini_puts("server", "host", "libs.example", path)
          && ini_putl("server", "port", 8080, path)
          && ini_putbool("server", "tls", 1, path)
          && ini_putf("server", "ratio", 2.5f, path)
          && ini_puts("paths", "data", "/var/data", path)
          && ini_puts("paths", "log", "/var/log", path);
    check(ok, "写入 6 个键（ini_puts/ini_putl/ini_putbool/ini_putf）");

    /* ② 读回 */
    char buf[128];
    int n = ini_gets("server", "host", "?", buf, sizeof(buf), path);
    check_detail(n == 12 && strcmp(buf, "libs.example") == 0, "ini_gets 读回 host", buf);
    check(ini_getl("server", "port", -1, path) == 8080, "ini_getl 读回 port=8080");
    check(ini_getbool("server", "tls", 0, path) == 1, "ini_getbool 读回 tls=true");
    snprintf(detail, sizeof(detail), "ratio=%.3f", (double)ini_getf("server", "ratio", 0.0f, path));
    check_detail(fabsf(ini_getf("server", "ratio", 0.0f, path) - 2.5f) < 1e-6f,
          "ini_getf 读回 ratio=2.5", detail);

    /* ③ 默认值语义 */
    ini_gets("server", "missing", "fallback", buf, sizeof(buf), path);
    check_detail(strcmp(buf, "fallback") == 0, "缺失键返回默认值", buf);
    check(ini_getl("nosuch", "port", 42, path) == 42, "缺失段返回默认值");

    /* ④ 存在性判定 */
    check(ini_haskey("server", "port", path) == 1
          && ini_haskey("server", "missing", path) == 0, "ini_haskey 判定正确");
    check(ini_hassection("paths", path) == 1
          && ini_hassection("nosuch", path) == 0, "ini_hassection 判定正确");

    /* ⑤ 枚举 */
    int sections = 0, keys = 0, browsed = 0;
    while (ini_getsection(sections, buf, sizeof(buf), path) > 0) {
        ++sections;
    }
    while (ini_getkey("paths", keys, buf, sizeof(buf), path) > 0) {
        ++keys;
    }
    ini_browse(count_cb, &browsed, path);
    snprintf(detail, sizeof(detail), "sections=%d keys(paths)=%d browsed=%d",
             sections, keys, browsed);
    check_detail(sections == 2 && keys == 2 && browsed == 6,
          "枚举：2 段 / paths 段 2 键 / browse 6 个键值对", detail);

    /* ⑥ 更新与删除 */
    check(ini_putl("server", "port", 9090, path)
          && ini_getl("server", "port", -1, path) == 9090, "覆盖写 port=9090");
    check(ini_puts("server", "tls", NULL, path)
          && ini_haskey("server", "tls", path) == 0, "ini_puts(...,NULL,...) 删除键");
    browsed = 0;
    ini_browse(count_cb, &browsed, path);
    check(browsed == 5, "删除后 browse 剩 5 个键值对");

    /* ⑦ 上游夹具文件的解析（尾随注释、无段落的"plain"格式） */
    snprintf(path, sizeof(path), "%s/test.ini", argv[1]);
    ini_gets("First", "String", "?", buf, sizeof(buf), path);
    snprintf(detail, sizeof(detail), "First.String=%s Second.Val=%ld", buf,
             ini_getl("Second", "Val", -1, path));
    check_detail(strcmp(buf, "noot") == 0, "上游夹具：尾随注释被正确剥离", detail);
    check(ini_getl("Second", "Val", -1, path) == 2, "上游夹具：Second.Val=2");
    snprintf(path, sizeof(path), "%s/testplain.ini", argv[1]);
    check(ini_getl(NULL, "Val", -1, path) == 1 || ini_getl("", "Val", -1, path) == 1,
          "上游夹具：无段落（plain）INI 读取");

    printf("消费者用例完成：%d/%d 步通过\n", g_checks - g_failed, g_checks);
    if (g_failed != 0) {
        printf("FAILED: %d\n", g_failed);
        return 1;
    }
    printf("Verdict: PASS\n");
    return 0;
}
