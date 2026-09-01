/*
 * test_log4c.c — log4c 1.2.4 Conan test_package（OHOS AArch64）
 *
 * 覆盖公开 API 主链路，全部为确定性断言：
 *   1. log4c_init() 初始化成功
 *   2. log4c_category_get() 获取/创建 category，验证名称与优先级
 *   3. 自定义 appender 类型（验证 log4c_appender_type_set 注册）
 *   4. 创建 appender、设置类型与自定义 layout（log4c_layout_set_type）
 *   5. log4c_category_set_appender/set_priority 绑定
 *   6. 输出确定日志内容，验证日志级别过滤（ERROR 放行、低优先级被拦）
 *   7. 校验最终输出内容与格式（渲染消息、优先级字符串）
 *   8. log4c_fini() 正常清理
 */
#include <log4c.h>
#include <log4c/appender.h>
#include <log4c/layout.h>
#include <log4c/category.h>
#include <log4c/init.h>
#include <log4c/priority.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define OUT_FILE "test_log4c.out"

static FILE *g_out = NULL;

/* ── 自定义 layout：把渲染消息包成固定前缀，输出内容可预测 ── */
static const char *test_layout_format(const log4c_layout_t *a_layout,
                                      const log4c_logging_event_t *a_event)
{
    static char buf[1024];
    (void)a_layout;
    snprintf(buf, sizeof(buf), "<%s> %s",
             log4c_priority_to_string(a_event->evt_priority),
             a_event->evt_msg);
    return buf;
}

static const log4c_layout_type_t test_layout_type = {
    "testlayout", test_layout_format,
};

/* ── 自定义 appender：写入内存文件流，供事后校验 ── */
static int test_appender_open(log4c_appender_t *a_appender)
{
    (void)a_appender;
    if (!g_out)
        g_out = fopen(OUT_FILE, "w");
    return g_out ? 0 : -1;
}

static int test_appender_append(log4c_appender_t *a_appender,
                                const log4c_logging_event_t *a_event)
{
    (void)a_appender;
    if (!g_out)
        return -1;
    return fprintf(g_out, "%s\n", a_event->evt_rendered_msg);
}

static int test_appender_close(log4c_appender_t *a_appender)
{
    (void)a_appender;
    if (g_out) {
        fclose(g_out);
        g_out = NULL;
    }
    return 0;
}

static const log4c_appender_type_t test_appender_type = {
    "testappender",
    test_appender_open,
    test_appender_append,
    test_appender_close,
};

static int check(int cond, const char *what)
{
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", what);
    return cond ? 0 : 1;
}

static int verify_output_file(void)
{
    FILE *fp = fopen(OUT_FILE, "r");
    char line[1024];
    int fails = 0;
    int nerror = 0, nwarn = 0, nfatal = 0, ninfo = 0;

    if (!fp) {
        printf("[FAIL] open %s for verification\n", OUT_FILE);
        return 1;
    }

    while (fgets(line, sizeof(line), fp)) {
        /* 每行必须以 "<LEVEL> " 开头（自定义 layout 格式） */
        if (strncmp(line, "<", 1) != 0) {
            printf("[FAIL] bad layout line: %s", line);
            fails++;
        }
        if (strstr(line, "<ERROR>"))
            nerror++;
        if (strstr(line, "<WARN>"))
            nwarn++;
        if (strstr(line, "<FATAL>"))
            nfatal++;
        if (strstr(line, "<INFO>"))
            ninfo++;
    }
    fclose(fp);

    /* 确定性断言：各级别输出行数（WARN 优先级下 INFO 被过滤） */
    fails += check(nerror == 1, "error-level lines == 1");
    fails += check(nwarn == 1, "warn-level lines == 1");
    fails += check(nfatal == 1, "fatal-level lines == 1");
    fails += check(ninfo == 0, "info-level lines == 0 (filtered)");
    return fails;
}

int main(void)
{
    int fails = 0;
    log4c_category_t *cat = NULL;
    log4c_appender_t *app = NULL;
    log4c_layout_t *layout = NULL;

    /* 1. 初始化 */
    fails += check(log4c_init() == 0, "log4c_init() == 0");

    /* 2. category：获取/创建、名称、默认优先级 */
    cat = log4c_category_get("test.cat");
    fails += check(cat != NULL, "log4c_category_get(\"test.cat\") != NULL");
    fails += check(strcmp(log4c_category_get_name(cat), "test.cat") == 0,
                   "category name == \"test.cat\"");

    /* 3. 注册自定义 appender/layout 类型 */
    fails += check(log4c_appender_type_set(&test_appender_type) == NULL,
                   "log4c_appender_type_set() registers new type");
    fails += check(log4c_appender_type_get("testappender") == &test_appender_type,
                   "log4c_appender_type_get(\"testappender\") roundtrip");
    fails += check(log4c_layout_type_set(&test_layout_type) == NULL,
                   "log4c_layout_type_set() registers new type");
    fails += check(log4c_layout_type_get("testlayout") == &test_layout_type,
                   "log4c_layout_type_get(\"testlayout\") roundtrip");

    /* 4. appender：创建、绑定类型、设置 layout
     * 注意：set_type/set_layout 返回的是「前一个类型」（头文件声明），
     * 新建 appender 默认类型为 stream，故此处断言 get_type 之后的类型。 */
    app = log4c_appender_get("testapp");
    fails += check(app != NULL, "log4c_appender_get(\"testapp\") != NULL");
    log4c_appender_set_type(app, &test_appender_type);
    fails += check(log4c_appender_get_type(app) == &test_appender_type,
                   "log4c_appender_set_type() then get_type() roundtrip");

    layout = log4c_layout_get("testlayout");
    fails += check(layout != NULL, "log4c_layout_get(\"testlayout\") != NULL");
    log4c_layout_set_type(layout, &test_layout_type);
    fails += check(log4c_layout_get_type(layout) == &test_layout_type,
                   "log4c_layout_set_type() then get_type() roundtrip");
    log4c_appender_set_layout(app, layout);

    /* 5. category 绑定 appender 与优先级 */
    log4c_category_set_appender(cat, app);
    log4c_category_set_priority(cat, LOG4C_PRIORITY_WARN);

    fails += check(log4c_category_get_priority(cat) == LOG4C_PRIORITY_WARN,
                   "category priority == WARN after set");

    /* 优先级字符串/数值转换（确定性 API 行为） */
    fails += check(strcmp(log4c_priority_to_string(LOG4C_PRIORITY_ERROR), "ERROR") == 0,
                   "priority_to_string(ERROR) == \"ERROR\"");
    fails += check(log4c_priority_to_int("WARN") == LOG4C_PRIORITY_WARN,
                   "priority_to_int(\"WARN\") == 400");

    /* 6. 输出确定日志内容（级别过滤：WARN 及以上放行，INFO 拦截） */
    log4c_category_error(cat, "error message %d", 42);
    log4c_category_warn(cat, "warn message");
    log4c_category_info(cat, "info must be filtered");
    log4c_category_fatal(cat, "fatal message");

    /* 7. 校验最终输出内容 */
    if (g_out) {
        fclose(g_out);
        g_out = NULL;
    }
    {
        FILE *fp = fopen(OUT_FILE, "r");
        char all[4096] = "";
        char line[1024];
        if (!fp) {
            printf("[FAIL] reopen %s\n", OUT_FILE);
            fails++;
        } else {
            while (fgets(line, sizeof(line), fp))
                strncat(all, line, sizeof(all) - strlen(all) - 1);
            fclose(fp);
        }
        fails += check(strstr(all, "<ERROR> error message 42") != NULL,
                       "output contains '<ERROR> error message 42'");
        fails += check(strstr(all, "<WARN> warn message") != NULL,
                       "output contains '<WARN> warn message'");
        fails += check(strstr(all, "<FATAL> fatal message") != NULL,
                       "output contains '<FATAL> fatal message'");
        fails += check(strstr(all, "info must be filtered") == NULL,
                       "INFO line filtered out by priority");
        fails += verify_output_file();
    }

    /* 8. 正常清理 */
    fails += check(log4c_fini() == 0, "log4c_fini() == 0");

    printf("test_log4c: %s (%d failed check(s))\n",
           fails == 0 ? "PASSED" : "FAILED", fails);
    return fails == 0 ? 0 : 1;
}
