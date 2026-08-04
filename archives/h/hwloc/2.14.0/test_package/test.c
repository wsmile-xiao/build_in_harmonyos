/* hwloc 2.14.0 真实功能断言。
 *
 * 判据分两层，**不能混**：
 *
 *   本文件（功能断言）—— 只测库的行为：拓扑发现、对象计数、bitmap 运算、XML 往返。
 *
 *   libxml2 / cairo 是否真接上 —— **本文件测不了，别装作能测**。
 *     hwloc 自带 topology-xml-nolibxml.c 内置解析器；即使置 HWLOC_LIBXML=1，
 *     topology-xml.c:3603 在 libxml_callbacks 为 NULL 时会**静默回落到 nolibxml 并成功**。
 *     所以「XML 往返过了」推不出「libxml2 接上了」。这两个依赖只能由产物核查判定
 *     （libhwloc.so 的 DT_NEEDED 含 libxml2、lstopo 的 DT_NEEDED 含 cairo）。
 *
 * 不用 dlopen 探针：解析到符号不等于函数能用。
 */
#include <hwloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int test_version(void)
{
    unsigned rt = hwloc_get_api_version();
    printf("hwloc 运行期 API 版本 0x%08x / 编译期宏 0x%08x\n", rt, HWLOC_API_VERSION);
    /* 运行期与编译期不一致 = 装出来的头和库不是同一次构建的，
     * 那是包本身的缺陷（混了两个版本），只比对其中一个发现不了。 */
    if (rt != HWLOC_API_VERSION) {
        printf("FAIL 运行期 0x%x 与编译期 0x%x 不一致（头库版本错配）\n", rt, HWLOC_API_VERSION);
        return 1;
    }
    if ((rt & 0xffff0000u) != 0x00020000u) {
        printf("FAIL API 版本 0x%x 不属于 2.x\n", rt);
        return 1;
    }
    return 0;
}

/* 拓扑发现是 hwloc 的本职。在鸿蒙上要真能读到 CPU 拓扑，
 * 而不是「初始化成功但一个对象都没有」。 */
static int test_topology(hwloc_topology_t *out)
{
    hwloc_topology_t t;
    int depth, pu_depth, npu, nmachine;

    if (hwloc_topology_init(&t) < 0) { printf("FAIL topology_init\n"); return 1; }
    if (hwloc_topology_load(t) < 0) {
        printf("FAIL topology_load —— 读不到本机拓扑（/sys 或 /proc 不可达？）\n");
        hwloc_topology_destroy(t); return 1;
    }

    depth = hwloc_topology_get_depth(t);
    printf("拓扑深度: %d\n", depth);
    if (depth < 2) {
        printf("FAIL 拓扑深度 %d < 2（至少要有 MACHINE + PU 两层）\n", depth);
        hwloc_topology_destroy(t); return 1;
    }

    /* 第 0 层必须是 MACHINE —— hwloc 的不变量，不成立说明拓扑构建坏了 */
    if (hwloc_get_depth_type(t, 0) != HWLOC_OBJ_MACHINE) {
        printf("FAIL 第 0 层不是 MACHINE\n");
        hwloc_topology_destroy(t); return 1;
    }
    nmachine = hwloc_get_nbobjs_by_depth(t, 0);
    if (nmachine != 1) {
        printf("FAIL MACHINE 对象数 %d != 1\n", nmachine);
        hwloc_topology_destroy(t); return 1;
    }

    pu_depth = hwloc_get_type_depth(t, HWLOC_OBJ_PU);
    if (pu_depth == HWLOC_TYPE_DEPTH_UNKNOWN) {
        printf("FAIL 找不到 PU 层 —— 没发现任何处理单元\n");
        hwloc_topology_destroy(t); return 1;
    }
    npu = hwloc_get_nbobjs_by_depth(t, pu_depth);
    printf("PU（逻辑处理器）数: %d\n", npu);
    /* 只断言下界。写死具体核数会在换机器时假失败。 */
    if (npu < 1) {
        printf("FAIL PU 数 %d < 1\n", npu);
        hwloc_topology_destroy(t); return 1;
    }

    *out = t;
    return 0;
}

/* cpuset 位运算 —— 纯本地计算，结果可手算，不依赖机器规格 */
static int test_bitmap(void)
{
    hwloc_bitmap_t a = hwloc_bitmap_alloc();
    hwloc_bitmap_t b = hwloc_bitmap_alloc();
    hwloc_bitmap_t r = hwloc_bitmap_alloc();
    char buf[64];
    int rc = 1;

    if (!a || !b || !r) { printf("FAIL bitmap_alloc 返回空\n"); goto out; }

    hwloc_bitmap_zero(a);
    hwloc_bitmap_set(a, 0); hwloc_bitmap_set(a, 2); hwloc_bitmap_set(a, 4);
    hwloc_bitmap_zero(b);
    hwloc_bitmap_set(b, 2); hwloc_bitmap_set(b, 3); hwloc_bitmap_set(b, 4);

    hwloc_bitmap_and(r, a, b);                       /* {0,2,4} ∩ {2,3,4} = {2,4} */
    if (hwloc_bitmap_weight(r) != 2 ||
        !hwloc_bitmap_isset(r, 2) || !hwloc_bitmap_isset(r, 4)) {
        printf("FAIL 交集应为 {2,4}，实得 weight=%d\n", hwloc_bitmap_weight(r));
        goto out;
    }

    hwloc_bitmap_or(r, a, b);                        /* 并集 = {0,2,3,4} */
    if (hwloc_bitmap_weight(r) != 4) {
        printf("FAIL 并集 weight 应为 4，实得 %d\n", hwloc_bitmap_weight(r));
        goto out;
    }

    hwloc_bitmap_andnot(r, a, b);                    /* {0,2,4} \ {2,3,4} = {0} */
    if (hwloc_bitmap_weight(r) != 1 || !hwloc_bitmap_isset(r, 0)) {
        printf("FAIL 差集应为 {0}，实得 weight=%d\n", hwloc_bitmap_weight(r));
        goto out;
    }

    /* list 格式是定值，可逐字符比对 */
    hwloc_bitmap_zero(r);
    hwloc_bitmap_set(r, 0); hwloc_bitmap_set(r, 1);
    hwloc_bitmap_set(r, 2); hwloc_bitmap_set(r, 7);
    if (hwloc_bitmap_list_snprintf(buf, sizeof buf, r) <= 0) {
        printf("FAIL bitmap_list_snprintf\n"); goto out;
    }
    if (strcmp(buf, "0-2,7") != 0) {
        printf("FAIL bitmap list 应为 \"0-2,7\"，实得 \"%s\"\n", buf);
        goto out;
    }
    hwloc_bitmap_zero(r);
    if (hwloc_bitmap_list_sscanf(r, "0-2,7") < 0) {
        printf("FAIL bitmap_list_sscanf\n"); goto out;
    }
    if (hwloc_bitmap_weight(r) != 4 || !hwloc_bitmap_isset(r, 7)) {
        printf("FAIL bitmap 字符串往返后内容不一致\n"); goto out;
    }

    printf("bitmap OK: 交/并/差 + list 字符串往返全部与手算一致\n");
    rc = 0;
out:
    hwloc_bitmap_free(a); hwloc_bitmap_free(b); hwloc_bitmap_free(r);
    return rc;
}

/* XML 往返：导出后重新导入，两份拓扑逐项一致。
 * 再说一遍：这条**不能**用来判 libxml2 是否接入（见文件头），它测的是序列化功能本身。 */
static int test_xml_roundtrip(hwloc_topology_t t)
{
    char *xml = NULL;
    int len = 0, rc = 1;
    hwloc_topology_t t2 = NULL;
    int d1, d2, n1, n2, pd1, pd2;

    if (hwloc_topology_export_xmlbuffer(t, &xml, &len, 0) < 0 || !xml || len <= 0) {
        printf("FAIL XML 导出失败\n"); return 1;
    }
    if (strncmp(xml, "<?xml", 5) != 0) {
        printf("FAIL 导出内容不是 XML（前 5 字节 \"%.5s\"）\n", xml); goto out;
    }

    if (hwloc_topology_init(&t2) < 0) { printf("FAIL 二次 topology_init\n"); goto out; }
    if (hwloc_topology_set_xmlbuffer(t2, xml, len) < 0) {
        printf("FAIL set_xmlbuffer —— XML 解析失败\n"); goto out;
    }
    if (hwloc_topology_load(t2) < 0) { printf("FAIL 从 XML 加载拓扑失败\n"); goto out; }

    d1 = hwloc_topology_get_depth(t);  d2 = hwloc_topology_get_depth(t2);
    if (d1 != d2) { printf("FAIL 往返后深度 %d != %d\n", d1, d2); goto out; }

    pd1 = hwloc_get_type_depth(t, HWLOC_OBJ_PU);
    pd2 = hwloc_get_type_depth(t2, HWLOC_OBJ_PU);
    n1 = hwloc_get_nbobjs_by_depth(t, pd1);
    n2 = hwloc_get_nbobjs_by_depth(t2, pd2);
    if (n1 != n2) { printf("FAIL 往返后 PU 数 %d != %d\n", n1, n2); goto out; }

    printf("XML 往返 OK: %d 字节，深度 %d、PU %d 逐项一致\n", len, d2, n2);
    rc = 0;
out:
    if (t2) hwloc_topology_destroy(t2);
    hwloc_free_xmlbuffer(t, xml);
    return rc;
}

int main(void)
{
    hwloc_topology_t t = NULL;

    if (test_version())        return 1;
    if (test_topology(&t))     return 1;
    if (test_bitmap())         { hwloc_topology_destroy(t); return 1; }
    if (test_xml_roundtrip(t)) { hwloc_topology_destroy(t); return 1; }

    hwloc_topology_destroy(t);
    printf("hwloc 2.14.0: 全部断言通过\n");
    return 0;
}
