/* libvpd 2.2.9 消费者测试（C++ 侧）
 *
 * 上游无测试套件，本文件为适配时补齐。
 * 目的：验证包内 C++ 库 libvpd_cxx.a 可被上层应用正常编译、链接、调用跑通。
 *       配方 package_info 声明 libs = ["vpd", "vpd_cxx"]，C++ 库随包发布，
 *       但此前的 C 用例只链接 C API，libvpd_cxx 从未被实际使用验证过 —— 本文件补上这一层。
 *
 * 覆盖：lsvpd 命名空间下 4 个公开类（libvpd_cxx.a 导出）
 *   - DataItem  ：默认构造 / 值构造 / getPackedLength / pack↔unpack 往返 /
 *                 访问器 / Source 管理（addSource / getNumSources / getSource /
 *                 getFirstSource，析构负责释放）
 *   - Source    ：构造 / 访问器
 *   - Component ：默认构造 / pack↔unpack 往返 / 析构
 *   - System    ：默认构造 / pack↔unpack 往返 / 析构
 *
 * ⚠️ 刻意规避的两处上游缺陷（会崩，不作为适配测试的判据）：
 *   1) DataItem::getSource(int i) 实现为 `if (i < getNumSources() || i == 0)`
 *      —— 无 source 时传 i=0 会越界访问空 vector（上游逻辑缺陷）。
 *      故本文件只在 addSource 之后调用 getSource(0)。
 *   2) DataItem::getValue()/访问器在未 setValue 时返回空串，属既定语义；
 *      不做「非空」断言，只做与构造入参一致的等值断言。
 *
 * ⚠️ 缓冲区所有权（上游文档明确）：pack(void**) 由 pack 自行 new[]，
 *    调用方负责 delete[]。解包方 unpack 不做任何内存管理。
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include <libvpd-2/Source.hpp>
#include <libvpd-2/component.hpp>
#include <libvpd-2/dataitem.hpp>
#include <libvpd-2/system.hpp>

using namespace std;
using namespace lsvpd;

static int g_checks = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        g_checks++;                                                         \
        if (!(cond)) {                                                      \
            fprintf(stderr, "  [FAIL] %s (line %d)\n", (msg), __LINE__);    \
            return 1;                                                       \
        }                                                                   \
    } while (0)

/* ── 1. DataItem( C++ )：默认构造 / 值构造 / 打包往返 ────────────── */
static int test_dataitem_roundtrip(void)
{
    /* 默认构造：空 ac / humanName / dataValue → getPackedLength() = 3 */
    DataItem empty;
    CHECK(empty.getPackedLength() == 3,
          "默认构造 DataItem::getPackedLength() 应为 3（仅 3 个 '\\0'）");

    /* 值构造：DataItem(string&) 设置 dataValue */
    string val = "test-value";
    DataItem di(val);
    CHECK(di.getValue() == val, "DataItem(string&) 未设置 dataValue");
    /* 3 + len(ac=0) + len(humanName=0) + len(dataValue) */
    const int expect_len = 3 + (int)val.length();
    CHECK(di.getPackedLength() == expect_len,
          "DataItem::getPackedLength() 与 3+len(dataValue) 不符");

    /* pack → 文本格式 ac\0humanName\0dataValue\0 */
    char *buf = new char[expect_len];
    const int written = di.pack(buf);
    CHECK(written == expect_len, "DataItem::pack() 返回长度与 getPackedLength() 不符");
    CHECK(strcmp(buf, "") == 0, "pack: ac 字段应为空串");
    CHECK(buf[1] == '\0', "pack: ac 字段未以 '\\0' 结束");
    CHECK(strcmp(buf + 1, "") == 0, "pack: humanName 字段应为空串");
    CHECK(strcmp(buf + 2, val.c_str()) == 0, "pack: dataValue 字段内容不符");

    /* unpack 往返：解包结果应与原对象等价 */
    DataItem du((const void *)buf);
    CHECK(du.getValue() == val, "unpack 往返后 dataValue 不一致");
    CHECK(du.getPackedLength() == expect_len, "unpack 往返后 getPackedLength 不一致");
    CHECK(du.getAC() == "", "unpack 往返后 ac 应为空串");
    CHECK(du.getHumanName() == "", "unpack 往返后 humanName 应为空串");

    delete[] buf;

    /* 二次往返：pack(unpack(x)) == x —— 序列化幂等 */
    char *buf2 = new char[expect_len];
    const int written2 = du.pack(buf2);
    CHECK(written2 == written, "二次 pack 长度不稳定");
    CHECK(memcmp(buf2, (const void *)"\0\0", 2) == 0, "二次 pack 前两字节应为空串");
    CHECK(strcmp(buf2 + 2, val.c_str()) == 0, "二次 pack dataValue 不一致");
    delete[] buf2;

    printf("  [1] C++ DataItem 默认/值构造 + pack↔unpack 往返 ok\n");
    return 0;
}

/* ── 2. Source + DataItem 的 source 管理 ───────────────────────── */
static int test_source(void)
{
    DataItem di;
    CHECK(di.getNumSources() == 0, "新建 DataItem 的 source 数应为 0");
    /* 无 source 时不调用 getSource(0)（上游该分支越界，见文件头说明） */
    CHECK(di.getFirstSource() == NULL, "无 source 时 getFirstSource() 应返回 NULL");

    /* Source(string srcRef, string data, int id, int type, int lines, int prefLevel) */
    Source *s = new Source("sysfs:/sys/devices/x", "node-x", 7, 1, 3, 100);
    CHECK(s->getSrcRef() == "sysfs:/sys/devices/x", "Source::getSrcRef 不符");
    CHECK(s->getData() == "node-x", "Source::getData 不符");
    CHECK(s->getID() == 7, "Source::getID 不符");
    CHECK(s->getType() == 1, "Source::getType 不符");
    CHECK(s->getLines() == 3, "Source::getLines 不符");
    CHECK(s->getPrefLvl() == 100, "Source::getPrefLvl 不符");
    /* ⚠️ 不调用 Source::getPackedLength()：上游 Source.hpp 声明了它，
     *    但 Source.cpp 中**没有定义**（全源码 grep Source::getPackedLength 无命中），
     *    链接期报 undefined symbol —— 属上游缺陷，非本适配可修（改上游源码越界），
     *    故测试规避之。 */

    /* addSource 接管所有权：此后由 ~DataItem 负责 delete，外部不可再释放 */
    di.addSource(s);
    CHECK(di.getNumSources() == 1, "addSource 后 source 数应为 1");
    CHECK(di.getSource(0) == s, "getSource(0) 应返回刚加入的 Source");
    CHECK(di.getFirstSource() == s, "getFirstSource() 应返回首个 Source");
    CHECK(di.getPrefLevelUsed() >= 0, "getPrefLevelUsed 应为非负");

    printf("  [2] C++ Source 构造/访问 + DataItem source 管理 ok\n");
    return 0;   /* di 析构负责释放 s */
}

/* ── 3. Component( C++ )：默认构造 / 打包往返 ───────────────────── */
static int test_component(void)
{
    Component c;
    /* getPackedSize 为私有；用 pack 的返回值作为长度判据 */
    void *buf = NULL;
    const unsigned int n = c.pack(&buf);
    CHECK(buf != NULL, "Component::pack() 未分配缓冲区");
    CHECK(n > 0, "Component::pack() 返回长度应 > 0");

    /* 解包往返：从打包缓冲重建，应可正常构造与析构（不崩、无泄漏） */
    Component cu((const void *)buf);

    /* 打包长度应与重新打包一致（结构自洽） */
    void *buf2 = NULL;
    const unsigned int n2 = cu.pack(&buf2);
    CHECK(buf2 != NULL, "Component(打包数据) 再 pack 未分配缓冲区");
    CHECK(n2 == n, "Component 打包长度往返不一致");

    delete[] (char *)buf;
    delete[] (char *)buf2;
    printf("  [3] C++ Component 默认构造 + pack↔unpack 往返 ok\n");
    return 0;
}

/* ── 4. System( C++ )：默认构造 / 打包往返 ──────────────────────── */
static int test_system(void)
{
    System s;
    CHECK(s.getID() == "/sys/bus", "System::getID 应为上游常量 /sys/bus");

    void *buf = NULL;
    const unsigned int n = s.pack(&buf);
    CHECK(buf != NULL, "System::pack() 未分配缓冲区");
    CHECK(n > 0, "System::pack() 返回长度应 > 0");

    System su((const void *)buf);
    void *buf2 = NULL;
    const unsigned int n2 = su.pack(&buf2);
    CHECK(buf2 != NULL, "System(打包数据) 再 pack 未分配缓冲区");
    CHECK(n2 == n, "System 打包长度往返不一致");

    delete[] (char *)buf;
    delete[] (char *)buf2;
    printf("  [4] C++ System 默认构造 + pack↔unpack 往返 ok\n");
    return 0;
}

int main(void)
{
    if (test_dataitem_roundtrip()) return 1;
    if (test_source()) return 1;
    if (test_component()) return 1;
    if (test_system()) return 1;

    printf("  [OK] libvpd C++ (libvpd_cxx) consumer test passed"
           "（共 %d 项检查通过）\n", g_checks);
    return 0;
}
