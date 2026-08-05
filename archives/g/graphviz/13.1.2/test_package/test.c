/* graphviz 13.1.2 真实功能断言。
 *
 * 核心是第 ③④ 条：**布局 + 渲染必须真跑通**。
 * graphviz 的布局引擎（dot/neato）和输出后端全是 **dlopen 加载的插件**
 * （libgvplugin_dot_layout.so 等），靠 lib/graphviz/config8 索引。
 * 那个索引由 `dot -c` 在安装后生成，而上游把这步挂在 install-exec-hook 上、
 * 条件是 `test "x$(DESTDIR)" = "x"`（cmd/dot/Makefile.am:68）——
 * conan 的 Autotools.install() **默认注入 DESTDIR**，必然跳过。
 *
 * 缺 config8 时 gvconfig.c:553 起的逻辑是 **静默 goto done**（源码注释原话
 * "silently return"），不报任何错，只是一个布局插件都没有。
 * 所以「构建绿 + 装包绿 + 只验 gvContext 非空」完全抓不到这个缺陷 ——
 * 必须真调 gvLayout + gvRenderData 才暴露。
 *
 * 不用 dlopen 探针：解析到 gvContext 不等于布局引擎能用。
 */
#include <graphviz/gvc.h>
#include <graphviz/cgraph.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* 一个 3 节点 3 边的有向图：a->b, b->c, a->c。
 * 节点/边数是定值，布局后的坐标也必须都有。 */
static const char *DOT_SRC =
    "digraph G {\n"
    "  a -> b;\n"
    "  b -> c;\n"
    "  a -> c;\n"
    "}\n";

static int test_version(GVC_t *gvc)
{
    char *v = gvcVersion(gvc);
    printf("graphviz 版本: %s\n", v ? v : "(null)");
    if (!v || !*v) { printf("FAIL gvcVersion 为空\n"); return 1; }
    if (strncmp(v, "13.", 3) != 0) {
        printf("FAIL 版本 %s 不是 13.x\n", v); return 1;
    }
    return 0;
}

/* cgraph 解析：节点边数可手算，且不依赖任何插件 —— 这是第 ③ 条的对照组。
 * 若这条也挂，说明问题在 cgraph 本身而非插件加载。 */
static int test_parse(Agraph_t **out)
{
    Agraph_t *g = agmemread(DOT_SRC);
    Agnode_t *n;

    if (!g) { printf("FAIL agmemread 返回空 —— DOT 解析失败\n"); return 1; }
    if (agnnodes(g) != 3) {
        printf("FAIL 节点数 %d != 3\n", agnnodes(g)); agclose(g); return 1;
    }
    if (agnedges(g) != 3) {
        printf("FAIL 边数 %d != 3\n", agnedges(g)); agclose(g); return 1;
    }
    /* 三个节点都要按名字找得到 */
    for (const char *nm = "abc"; *nm; nm++) {
        char buf[2] = { *nm, 0 };
        n = agnode(g, buf, 0);          /* createflag=0：只查不建 */
        if (!n) { printf("FAIL 找不到节点 \"%s\"\n", buf); agclose(g); return 1; }
    }
    /* 不存在的节点必须查不到 —— 只验"找得到"的话，
     * 一个永远返回非空的实现也能通过 */
    if (agnode(g, (char *)"zzz", 0) != NULL) {
        printf("FAIL 不存在的节点 \"zzz\" 竟然查到了\n"); agclose(g); return 1;
    }
    printf("cgraph 解析 OK: 3 节点 3 边，按名查找正反例均正确\n");
    *out = g;
    return 0;
}

/* 布局 —— 必须真加载 dot_layout 插件 */
static int test_layout(GVC_t *gvc, Agraph_t *g)
{
    Agnode_t *n;
    int i, with_pos = 0;

    if (gvLayout(gvc, g, "dot") != 0) {
        printf("FAIL gvLayout(\"dot\") 失败 —— dot_layout 插件没加载。\n");
        printf("     多半是 lib/graphviz/config8 没生成（`dot -c` 未在安装后执行）。\n");
        printf("     gvconfig.c 在配置缺失时是**静默返回**，不会报错，只是没有插件。\n");
        return 1;
    }

    /* 布局后每个节点都该有坐标；全为 0 说明布局没真跑 */
    for (i = 0; i < 3; i++) {
        char buf[2] = { (char)('a' + i), 0 };
        n = agnode(g, buf, 0);
        if (!n) { printf("FAIL 布局后找不到节点 %s\n", buf); return 1; }
        if (ND_coord(n).x != 0.0 || ND_coord(n).y != 0.0) with_pos++;
    }
    if (with_pos < 2) {
        printf("FAIL 只有 %d 个节点拿到非零坐标（3 个里至少该有 2 个）—— 布局未真正执行\n",
               with_pos);
        return 1;
    }
    printf("dot 布局 OK: %d/3 个节点有非零坐标 —— dot_layout 插件已加载\n", with_pos);
    return 0;
}

/* 渲染 —— 必须真加载输出后端插件 */
static int test_render(GVC_t *gvc, Agraph_t *g)
{
    char *data = NULL;
    size_t len = 0;
    int rc = 1;

    if (gvRenderData(gvc, g, "svg", &data, &len) != 0 || !data || len == 0) {
        printf("FAIL gvRenderData(\"svg\") 失败 —— svg 输出插件没加载\n");
        return 1;
    }
    /* 内容必须真是 SVG，而且含得到三个节点名 —— 只看"非空"抓不到空壳输出 */
    if (len < 32 || !strstr(data, "<svg")) {
        printf("FAIL 输出不含 <svg（前 40 字节: %.40s）\n", data); goto out;
    }
    if (!strstr(data, ">a<") && !strstr(data, "\">a</")) {
        /* 节点标签在 <text ...>a</text> 里 */
        if (!strstr(data, ">a</text>")) {
            printf("FAIL SVG 里找不到节点 a 的标签\n"); goto out;
        }
    }
    if (!strstr(data, ">c</text>")) {
        printf("FAIL SVG 里找不到节点 c 的标签\n"); goto out;
    }
    printf("SVG 渲染 OK: %zu 字节，含 <svg 且三个节点标签齐全 —— 输出插件已加载\n", len);
    rc = 0;
out:
    gvFreeRenderData(data);
    return rc;
}

/* PNG 渲染 —— 走 gd 或 cairo 后端，能出说明图像插件链真通 */
static int test_render_png(GVC_t *gvc, Agraph_t *g)
{
    char *data = NULL;
    size_t len = 0;

    if (gvRenderData(gvc, g, "png", &data, &len) != 0 || !data || len == 0) {
        printf("FAIL gvRenderData(\"png\") 失败 —— gd/cairo 图像后端没接上\n");
        return 1;
    }
    if (len < 8 || memcmp(data, "\x89PNG\r\n\x1a\n", 8) != 0) {
        printf("FAIL 输出不是 PNG（魔数不符）\n");
        gvFreeRenderData(data); return 1;
    }
    printf("PNG 渲染 OK: %zu 字节，魔数正确 —— 图像后端（gd/cairo）已接入\n", len);
    gvFreeRenderData(data);
    return 0;
}

int main(void)
{
    GVC_t *gvc;
    Agraph_t *g = NULL;
    int rc = 1;

    gvc = gvContext();
    if (!gvc) { printf("FAIL gvContext 返回空\n"); return 1; }

    if (test_version(gvc))      goto out;
    if (test_parse(&g))         goto out;
    if (test_layout(gvc, g))    goto out;
    if (test_render(gvc, g))    goto out;
    if (test_render_png(gvc, g))goto out;

    printf("graphviz 13.1.2: 全部断言通过\n");
    rc = 0;
out:
    if (g) { gvFreeLayout(gvc, g); agclose(g); }
    gvFreeContext(gvc);
    return rc;
}
