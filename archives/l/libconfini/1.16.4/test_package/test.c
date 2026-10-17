/* libconfini 1.16.4 真实功能断言（test_package 消费者测试）.
 *
 * 链接的是打包后的 libconfini.so / libconfini.a（不包含源码目录），
 * 通过 load_ini_path() 解析一个真实 INI 文件，在回调里逐节点断言。
 *
 * 覆盖：
 *   1. INI 文本解析（load_ini_path + IniDispatch 回调分发）
 *   2. section / key / value 内容（data / value / append_to）
 *   3. 回调返回的节点类型（INI_SECTION / INI_KEY / INI_DISABLED_*）
 *   4. 边界/格式行为：隐式值（implicit）、disabled 条目嵌在注释里、
 *      数组拆分 ini_array_split、大小写不敏感匹配 ini_string_match_ii
 *   5. 返回值检查（CONFINI_SUCCESS / 错误码）
 *
 * 不用 dlopen 探针：解析到符号不等于解析器真能正确分发。
 * 失败后立即 return 1，绝不继续用无效数据。
 */
#include <confini.h>

#include <stdio.h>
#include <string.h>

/* ── 收集到的解析结果（回调里写入，main 里断言）── */
#define MAX_NODES 32

typedef struct {
    uint_least8_t type;
    const char *data;     /* 指向 dispatch->data（库内部缓冲，回调期间有效 → 立刻拷贝） */
    char data_buf[128];
    const char *value;
    char value_buf[128];
    const char *append_to;
    char append_to_buf[128];
} CaughtNode;

static CaughtNode g_nodes[MAX_NODES];
static int g_node_count = 0;
static int g_stats_members = -1;   /* IniStatistics.members，-1 = 未回调 */

static void copy_str(char *dst, const char *src, size_t cap)
{
    if (!src) { dst[0] = 0; return; }
    size_t n = strlen(src);
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n);
    dst[n] = 0;
}

/* f_init：拿到文件级统计 */
static int stats_cb(IniStatistics *statistics, void *v_null)
{
    (void)v_null;
    g_stats_members = (int)statistics->members;
    return 0;
}

/* f_foreach：每个节点都拷贝下来，返回 0 继续 */
static int dispatch_cb(IniDispatch *disp, void *v_null)
{
    (void)v_null;
    if (g_node_count >= MAX_NODES) {
        return 1;   /* 超预期：中断，被测为失败 */
    }
    CaughtNode *n = &g_nodes[g_node_count++];
    n->type = disp->type;
    copy_str(n->data_buf, disp->data, sizeof n->data_buf);
    n->data = n->data_buf;
    copy_str(n->value_buf, disp->value, sizeof n->value_buf);
    n->value = n->value_buf;
    copy_str(n->append_to_buf, disp->append_to, sizeof n->append_to_buf);
    n->append_to = n->append_to_buf;
    return 0;
}

/* 在已捕获节点里按 type+data 查找 */
static CaughtNode *find_node(uint_least8_t type, const char *data)
{
    for (int i = 0; i < g_node_count; i++) {
        if (g_nodes[i].type == type && strcmp(g_nodes[i].data, data) == 0)
            return &g_nodes[i];
    }
    return NULL;
}

#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("FAIL " __VA_ARGS__); printf("\n"); return 1; } } while (0)

/* 数组拆分回调：累计被拆出的元素数 */
static int array_count_cb(char *str, size_t len, size_t num, IniFormat fmt, void *v_counter)
{
    (void)str; (void)len; (void)num; (void)fmt;
    (*(int *)v_counter)++;
    return 0;
}

int main(void)
{
    const char *ini_path = "test_data.ini";
    int rc;

    /* ── ① load_ini_path 返回值校验：合法文件必须返回 CONFINI_SUCCESS(0) ── */
    rc = load_ini_path(ini_path, INI_DEFAULT_FORMAT,
                       stats_cb, dispatch_cb, NULL);
    CHECK(rc == CONFINI_SUCCESS,
          "load_ini_path 返回 %d（期望 CONFINI_SUCCESS=0）", rc);
    printf("① load_ini_path OK: rc=%d, 统计 members=%d, 捕获节点=%d\n",
           rc, g_stats_members, g_node_count);

    /* ── ② section 解析：[server] 段必须作为 INI_SECTION 出现 ── */
    CaughtNode *sec = find_node(INI_SECTION, "server");
    CHECK(sec != NULL, "未找到 INI_SECTION \"server\"");
    printf("② section OK: type=%u data=\"%s\" append_to=\"%s\"\n",
           (unsigned)sec->type, sec->data, sec->append_to);

    /* ── ③ key/value：host = 127.0.0.1 ── */
    CaughtNode *host = find_node(INI_KEY, "host");
    CHECK(host != NULL, "未找到 INI_KEY \"host\"");
    CHECK(strcmp(host->value, "127.0.0.1") == 0,
          "host value=\"%s\"（期望 127.0.0.1）", host->value);
    CHECK(strcmp(host->append_to, "server") == 0,
          "host append_to=\"%s\"（期望 server）", host->append_to);
    printf("③ key/value OK: host=\"%s\" value=\"%s\" append_to=\"%s\"\n",
           host->data, host->value, host->append_to);

    /* ── ④ 数组值：ports = 8080, 8081, 8082 → ini_array_split 拆出 3 个 ── */
    CaughtNode *ports = find_node(INI_KEY, "ports");
    CHECK(ports != NULL, "未找到 INI_KEY \"ports\"");
    {
        /* ini_array_split 原地改写字符串，需可写缓冲 */
        char mutval[128];
        copy_str(mutval, ports->value, sizeof mutval);
        int count = 0;
        int arc = ini_array_split(mutval, INI_COMMA, INI_DEFAULT_FORMAT,
                                  array_count_cb, &count);
        CHECK(arc == 0, "ini_array_split 返回 %d", arc);
        CHECK(count == 3, "ports 拆出 %d 个元素（期望 3）", count);
        printf("④ ini_array_split OK: ports 拆出 %d 个元素\n", count);
    }

    /* ── ⑤ 隐式值（implicit value）：debug = （无值）→ value 为隐式 ── */
    CaughtNode *debug = find_node(INI_KEY, "debug");
    CHECK(debug != NULL, "未找到 INI_KEY \"debug\"");
    /* 默认 INI_GLOBAL_IMPLICIT_VALUE = NULL, v_len = 0；空值键的 value 应为隐式值 */
    CHECK(debug->value == NULL || debug->value[0] == 0,
          "debug value=\"%s\"（期望隐式/空）", debug->value ? debug->value : "(null)");
    printf("⑤ 隐式值 OK: debug value=%s（隐式）\n",
           debug->value ? "(empty)" : "(null)");

    /* ── ⑥ disabled 条目：;old_port = 21 嵌在注释里 → INI_DISABLED_KEY ── */
    CaughtNode *oldport = find_node(INI_DISABLED_KEY, "old_port");
    CHECK(oldport != NULL, "未找到 INI_DISABLED_KEY \"old_port\"");
    CHECK(strcmp(oldport->value, "21") == 0,
          "old_port value=\"%s\"（期望 21）", oldport->value);
    printf("⑥ disabled 条目 OK: type=%u old_port=\"%s\" value=\"%s\"\n",
           (unsigned)oldport->type, oldport->data, oldport->value);

    /* ── ⑦ disabled 段：;[legacy] → INI_DISABLED_SECTION ── */
    CaughtNode *legacy = find_node(INI_DISABLED_SECTION, "legacy");
    CHECK(legacy != NULL, "未找到 INI_DISABLED_SECTION \"legacy\"");
    printf("⑦ disabled 段 OK: type=%u legacy=\"%s\"\n",
           (unsigned)legacy->type, legacy->data);

    /* ── ⑧ 大小写不敏感匹配：ini_string_match_ii ── */
    CHECK(ini_string_match_ii("HOST", "host", INI_DEFAULT_FORMAT) == true,
          "ini_string_match_ii(\"HOST\",\"host\") 应匹配");
    CHECK(ini_string_match_ii("host", "ports", INI_DEFAULT_FORMAT) == false,
          "ini_string_match_ii(\"host\",\"ports\") 不应匹配");
    printf("⑧ ini_string_match_ii OK: 大小写不敏感匹配正确\n");

    /* ── ⑨ 边界：不存在的文件必须返回错误（CONFINI_ENOENT=4）── */
    g_node_count = 0;
    rc = load_ini_path("definitely_missing_file.ini", INI_DEFAULT_FORMAT,
                       stats_cb, dispatch_cb, NULL);
    CHECK((rc & CONFINI_ERROR) != 0 || rc == CONFINI_ENOENT,
          "缺失文件返回 %d（期望含 CONFINI_ERROR 或 ENOENT=4）", rc);
    CHECK(g_node_count == 0,
          "缺失文件不应分发任何节点（实际 %d）", g_node_count);
    printf("⑨ 缺失文件 OK: rc=%d, 无节点分发\n", rc);

    /* ── ⑩ strip_ini_cache 直接解析内存缓冲（不经过文件 I/O）── */
    {
        char buf[] = "name=libconfini";
        g_node_count = 0;
        rc = strip_ini_cache(buf, sizeof(buf) - 1, INI_DEFAULT_FORMAT,
                             NULL, dispatch_cb, NULL);
        CHECK(rc == CONFINI_SUCCESS,
              "strip_ini_cache 返回 %d（期望 0）", rc);
        CaughtNode *name = find_node(INI_KEY, "name");
        CHECK(name != NULL, "strip_ini_cache 未分发 key \"name\"");
        CHECK(strcmp(name->value, "libconfini") == 0,
              "name value=\"%s\"（期望 libconfini）", name->value);
        printf("⑩ strip_ini_cache OK: 内存解析 name=\"%s\" value=\"%s\"\n",
               name->data, name->value);
    }

    printf("libconfini 1.16.4: 全部断言通过\n");
    return 0;
}
