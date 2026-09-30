/* libvpd 2.2.9 消费者测试（C 侧）
 *
 * 上游无测试套件，本文件为适配时补齐。
 * 目的（赛事自检第 5 条）：模拟上层应用调用该库对外公开 API，
 * 验证库能被别人拿去正常编译、链接、调用跑通。
 *
 * 覆盖范围：上游全部 6 个公开 C 头文件的 24 个函数 ——
 *   common.h(3) / dataitem.h(5) / component.h(4) / system.h(3) /
 *   vpddbenv.h(4) / vpdretriever.h(5)
 * 其中需要真实 VPD 硬件数据的接口（fetch_x / get_x 命中数据分支）无法在
 * 无 PowerPC VPD 设备的 OHOS 上产生有效数据，故对这些接口只断言
 * 「空库/空指针下的既定契约」（返回 NULL、不崩溃），不制造假失败。
 *
 * ⚠️ 不能用 assert()：本库构建带 -DNDEBUG（见 conanfile 的 Release 配置），
 *    断言会被编译器完全移除，判空失效会导致 NULL 解引用。
 *    故统一改用下面的 CHECK 宏（显式判空并返回非零）。
 *
 * ⚠️ 释放语义（读上游源码确认，写错即双重释放/泄漏）：
 *    - free_dataitem()  会遍历 next 链整链释放 → 链上勿再逐个 free
 *    - free_component() 无 NULL 守卫，且**不**遍历 next 链 → 链上须逐个 free
 *    - free_list()      会连带 free(head->data) → data 必须是可 free 的指针
 */
/* strdup 属 POSIX，需显式声明特性宏（-std=c99 严格模式下其原型不可见 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <libvpd-2/common.h>
#include <libvpd-2/component.h>
#include <libvpd-2/dataitem.h>
#include <libvpd-2/system.h>
#include <libvpd-2/vpddbenv.h>
#include <libvpd-2/vpdretriever.h>

static int g_checks = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        g_checks++;                                                         \
        if (!(cond)) {                                                      \
            fprintf(stderr, "  [FAIL] %s (line %d)\n", (msg), __LINE__);    \
            return 1;                                                       \
        }                                                                   \
    } while (0)

/* ── 1. dataitem.h ─────────────────────────────────────────────── */
static int test_dataitem(void)
{
    struct dataitem *di = new_dataitem();
    CHECK(di != NULL, "new_dataitem returned NULL");
    CHECK(di->next == NULL, "new_dataitem 应返回零初始化（next 非 NULL）");
    di->humanName = strdup("Model Name");
    di->ac        = strdup("MN");
    di->dataValue = strdup("test-value");
    CHECK(di->humanName && di->ac && di->dataValue, "strdup failed");

    /* calc_packed_length_dataitem 的公式：3 + len(ac) + len(dataValue) + len(humanName)
     * = 3 + 2("MN") + 10("test-value") + 10("Model Name") = 25（精确值断言，强于 > 0） */
    int packed = calc_packed_length_dataitem(di);
    printf("  [1] new_dataitem ok, packed_length=%d\n", packed);
    CHECK(packed == 25, "calc_packed_length_dataitem() 应为 25");

    /* 空指针契约：上游 return 0 */
    CHECK(calc_packed_length_dataitem(NULL) == 0,
          "calc_packed_length_dataitem(NULL) 应返回 0");

    /* free_dataitem() 内部已释放 humanName/ac/dataValue，且会遍历 next 链，
     * 此处不可再手动 free（否则双重释放，OHOS musl 下 SIGTRAP） */
    free_dataitem(di);
    free_dataitem(NULL);          /* 上游 while(freeme) → NULL 安全 */
    return 0;
}

/* ── 2. dataitem.h 的 add / unpack（此前未覆盖）────────────────── */
static int test_dataitem_add_unpack(void)
{
    /* add_dataitem：追加到 next 链尾 */
    struct dataitem *d1 = new_dataitem();
    struct dataitem *d2 = new_dataitem();
    CHECK(d1 && d2, "new_dataitem for chain failed");
    add_dataitem(d1, d2);
    CHECK(d1->next == d2, "add_dataitem 未把 addme 接到链尾");

    /* 空参契约：上游 !head || !addme → 直接 return（不崩） */
    add_dataitem(NULL, d2);
    add_dataitem(d1, NULL);
    CHECK(d1->next == d2, "add_dataitem 空参调用后链被改动");

    /* free_dataitem 遍历整链，会一并释放 d2 */
    free_dataitem(d1);

    /* unpack_dataitem：文本格式 ac\0humanName\0dataValue\0（手工构造合法缓冲） */
    CHECK(unpack_dataitem(NULL) == NULL, "unpack_dataitem(NULL) 应返回 NULL");

    static char buf[] = "MN\0Model Name\0test-value\0";
    struct dataitem *u = unpack_dataitem(buf);
    CHECK(u != NULL, "unpack_dataitem 合法缓冲返回 NULL");
    CHECK(strcmp(u->ac, "MN") == 0, "unpack: ac 不一致");
    CHECK(strcmp(u->humanName, "Model Name") == 0, "unpack: humanName 不一致");
    CHECK(strcmp(u->dataValue, "test-value") == 0, "unpack: dataValue 不一致");

    /* 往返一致性：解包结果重新计算打包长度应与原值一致 */
    CHECK(calc_packed_length_dataitem(u) == 25,
          "unpack→calc_packed_length 往返不一致（应为 25）");
    free_dataitem(u);
    printf("  [2] dataitem add/unpack 往返 ok\n");
    return 0;
}

/* ── 3. common.h 的 list 三函数（此前完全未覆盖）──────────────── */
static int test_list(void)
{
    struct list *l1 = new_list();
    int *payload = (int *)malloc(sizeof(int));
    CHECK(l1 != NULL, "new_list returned NULL");
    CHECK(payload != NULL, "malloc payload failed");
    *payload = 42;

    CHECK(l1->next == NULL, "new_list 应返回零初始化（next 非 NULL）");
    l1->data = payload;           /* free_list 会 free 它，必须是堆指针 */

    /* concat_list 空参契约：上游 !head || !addme → return NULL */
    CHECK(concat_list(NULL, l1) == NULL, "concat_list(NULL, x) 应返回 NULL");
    CHECK(concat_list(l1, NULL) == NULL, "concat_list(x, NULL) 应返回 NULL");

    struct list *l2 = new_list();
    CHECK(l2 != NULL, "new_list(second) returned NULL");
    struct list *head = concat_list(l1, l2);
    CHECK(head == l1, "concat_list 应返回原 head");
    CHECK(l1->next == l2, "concat_list 未把 addme 接到链尾");

    /* 判据：链结构确实成立，且 data 贯穿未变 */
    CHECK(l1->data == payload && *(int *)l1->data == 42,
          "list data 载荷丢失");
    CHECK(l1->next->data == NULL && l1->next->next == NULL,
          "l2 应为零初始化节点");

    free_list(l1);                /* 整链释放（含 l1->data） */
    free_list(NULL);              /* 上游 while(head) → NULL 安全 */
    printf("  [3] common.h list 三函数 ok\n");
    return 0;
}

/* ── 4. component.h ───────────────────────────────────────────── */
static int test_component(void)
{
    /* new_component(1) 初始化约 40 个 dataitem 字段，纯内存路径 */
    struct component *c = new_component(1);
    printf("  [4] new_component(1) -> %s\n", c ? "non-NULL" : "NULL");
    CHECK(c != NULL, "new_component returned NULL");
    CHECK(c->id != NULL && c->id->humanName != NULL,
          "component->id 未按 init=1 初始化");
    free_component(c);            /* 无 NULL 守卫，只传有效指针 */

    /* unpack_component 二进制格式，无法手工构造有效缓冲 →
     * 只断言文档化的 NULL 契约（上游 if(!buffer) return NULL） */
    CHECK(unpack_component(NULL) == NULL, "unpack_component(NULL) 应返回 NULL");

    /* add_component：追加到 next 链尾；空参契约 */
    struct component *c1 = new_component(0);
    struct component *c2 = new_component(0);
    CHECK(c1 && c2, "new_component(0) for chain failed");
    add_component(c1, c2);
    CHECK(c1->next == c2, "add_component 未把 addme 接到链尾");
    add_component(NULL, c2);
    add_component(c1, NULL);
    CHECK(c1->next == c2, "add_component 空参调用后链被改动");

    /* free_component 不遍历 next 链 → 须逐个释放（顺序无关，因不触碰 next） */
    free_component(c1);
    free_component(c2);
    printf("  [4] component add/unpack 契约 ok\n");
    return 0;
}

/* ── 5. system.h ──────────────────────────────────────────────── */
static int test_system(void)
{
    struct system *s = new_system(1);
    printf("  [5] new_system(1) -> %s\n", s ? "non-NULL" : "NULL");
    CHECK(s != NULL, "new_system returned NULL");
    CHECK(s->id != NULL, "system->id 未按 init=1 初始化");
    free_system(s);
    free_system(NULL);            /* 上游 if(!freeme) return → NULL 安全 */

    /* unpack_system 二进制格式 → 只断言 NULL 契约 */
    CHECK(unpack_system(NULL) == NULL, "unpack_system(NULL) 应返回 NULL");
    printf("  [5] system unpack 契约 ok\n");
    return 0;
}

/* ── 6. vpddbenv.h + vpdretriever.h ───────────────────────────── */
static int test_db_and_retriever(const char *testdir)
{
    struct vpddbenv *env = new_vpddbenv(testdir, "vpd.db");
    const int env_ok = (env != NULL);
    if (env_ok) {
        printf("  [6] new_vpddbenv ok, envDir=%s dbFileName=%s\n",
               env->envDir, env->dbFileName);
        CHECK(strcmp(env->envDir, testdir) == 0, "envDir 与传入目录不一致");
        CHECK(strcmp(env->dbFileName, "vpd.db") == 0, "dbFileName 与传入文件名不一致");
        CHECK(strlen(env->fullPath) > 0, "fullPath 为空");

        /* fetch_* 的「空库」契约：new_vpddbenv 只 sqlite3_open，不建表；
         * 对无表库查询应在错误路径返回 NULL 而非崩溃。
         * （需真实 VPD 数据的成功分支无法在 OHOS 上复现，故只验此契约） */
        struct component *fc = fetch_component(env, "nonexistent-id");
        CHECK(fc == NULL, "空库 fetch_component 应返回 NULL");
        if (fc) free_component(fc);

        struct system *fs = fetch_system(env);
        CHECK(fs == NULL, "空库 fetch_system 应返回 NULL");
        if (fs) free_system(fs);
        printf("  [6] fetch_* 空库契约 ok\n");
    } else {
        printf("  [6] new_vpddbenv 返回 NULL（目录 '%s' 下无法建库），"
               "按上游语义属可接受结果\n", testdir);
    }

    /* vpdretriever：new 是 new_vpddbenv 的薄包装，成败必然一致 */
    struct vpdretriever *r = new_vpdretriever(testdir, "vpd.db");
    printf("  [6] new_vpdretriever -> %s\n", r ? "non-NULL" : "NULL");
    CHECK((r == NULL) == !env_ok,
          "new_vpdretriever 与 new_vpddbenv 成败不一致（前者为后者的薄包装）");

    /* get_* 的 NULL 守卫契约（上游均 if(!dbenv) return NULL）——
     * 这部分不需要任何硬件/数据库即可判定 */
    CHECK(get_system(NULL) == NULL, "get_system(NULL) 应返回 NULL");
    CHECK(get_component(NULL, "x") == NULL, "get_component(NULL, x) 应返回 NULL");
    CHECK(get_component_tree(NULL) == NULL, "get_component_tree(NULL) 应返回 NULL");

    if (r != NULL) {
        /* 有实例时，get_* 在空库上同样应安全返回 NULL（不崩） */
        struct system *gs = get_system(r);
        CHECK(gs == NULL, "空库 get_system 应返回 NULL");
        if (gs) free_system(gs);

        struct component *gc = get_component(r, "nonexistent-id");
        CHECK(gc == NULL, "空库 get_component 应返回 NULL");
        if (gc) free_component(gc);

        struct system *gt = get_component_tree(r);
        CHECK(gt == NULL, "空库 get_component_tree 应返回 NULL");
        if (gt) free_system(gt);
        printf("  [6] get_* 空库契约 ok\n");

        free_vpdretriever(r);
    }
    free_vpdretriever(NULL);      /* 上游 if(!freeme) return → NULL 安全 */
    if (env_ok) free_vpddbenv(env);
    free_vpddbenv(NULL);
    return 0;
}

int main(void)
{
    const char *testdir = "./vpd-test-dir";
    mkdir(testdir, 0755);         /* 已存在时返回 EEXIST，可忽略 */

    if (test_dataitem()) return 1;
    if (test_dataitem_add_unpack()) return 1;
    if (test_list()) return 1;
    if (test_component()) return 1;
    if (test_system()) return 1;
    if (test_db_and_retriever(testdir)) return 1;

    printf("  [OK] libvpd consumer test passed（共 %d 项检查通过）\n", g_checks);
    return 0;
}
