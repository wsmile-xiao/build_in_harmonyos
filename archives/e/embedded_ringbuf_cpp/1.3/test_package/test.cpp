/* test_package/test.cpp — embedded_ringbuf_cpp 1.3 消费者测试（鸿蒙特有测试行）
 *
 * 交付口径：header-only 模板库必须**实例化真实消费者**，只编译不算测。
 * 统计单位 = 消费者用例数（RUN 计数），与上游用例数分栏、不进上游分母。
 *
 * 第一个 include 就是交付的 <RingBufCPP.h>（README 记载的用法）：
 *   - 未打补丁时该头使用 size_t 却不含任何定义 size_t 的标准头，
 *     此处必然 `unknown type name 'size_t'`（上游原样实测 rc=1）；
 *   - 因此这一行同时钉死「测试靶向 == 交付物」——本 TU 编不过就说明
 *     package() 交付的头不是被打过 0001 补丁的那一份。
 *
 * 已知限制（如实申报，不写成通过项）：OHOS/非 Arduino 分支里
 * RB_ATOMIC_START/END 只是普通 `{ }`，**没有**真实的中断/线程互斥，
 * 所以本文件不写多线程并发用例（写了会是真竞态），只断言宏抽象在
 * OHOS 上已定义且可嵌套；ISR/线程安全需由使用方自行实现这两个宏
 * （上游 README "Supported Platforms" 明示）。
 */
#include <RingBufCPP.h>

#include <cstdint>
#include <cstdio>
#include <cstring>

/* ---------- 极简断言框架（消费者视角，不引入第三方测试框架） ---------- */
static int g_cases = 0;
static int g_case_fail = 0;
static int g_asserts = 0;
static int g_assert_fail = 0;

static void check(bool cond, const char *expr, const char *file, int line)
{
    ++g_asserts;
    if (!cond) {
        ++g_assert_fail;
        std::printf("    ASSERT-FAIL %s:%d: %s\n", file, line, expr);
    }
}

#define CHECK(cond) check((cond), #cond, __FILE__, __LINE__)

#define RUN(fn)                                                     \
    do {                                                            \
        ++g_cases;                                                  \
        int _before = g_assert_fail;                                \
        fn();                                                       \
        bool _ok = (g_assert_fail == _before);                      \
        if (!_ok) {                                                 \
            ++g_case_fail;                                          \
        }                                                           \
        std::printf("case %02d %-34s %s\n", g_cases, #fn,           \
                    _ok ? "PASS" : "FAIL");                         \
    } while (0)

/* ---------- 用例 1：add/pull 保 FIFO 顺序 ---------- */
static void case_add_pull_fifo_order(void)
{
    RingBufCPP<int, 8> q;
    for (int i = 1; i <= 5; ++i) {
        CHECK(q.add(i));
    }
    CHECK(q.numElements() == 5);
    for (int i = 1; i <= 5; ++i) {
        int out = -1;
        CHECK(q.pull(&out));
        CHECK(out == i);
    }
    CHECK(q.isEmpty());
}

/* ---------- 用例 2：空缓冲 pull 被拒绝且不改动出参 ---------- */
static void case_empty_pull_rejected(void)
{
    RingBufCPP<int, 4> q;
    int dest = 0x5A5A;
    CHECK(!q.pull(&dest));
    CHECK(dest == 0x5A5A);
    CHECK(q.isEmpty());
}

/* ---------- 用例 3：容量边界（恰好 MaxElements 即 full） ---------- */
static void case_capacity_full_boundary(void)
{
    RingBufCPP<int, 4> q;
    CHECK(!q.isFull());
    for (int i = 0; i < 4; ++i) {
        CHECK(!q.isFull());
        CHECK(q.add(i));
    }
    CHECK(q.isFull());
    CHECK(q.numElements() == 4);
}

/* ---------- 用例 4：满且不覆盖 → add 返回 false 且内容不变 ---------- */
static void case_reject_when_full_no_overwrite(void)
{
    RingBufCPP<int, 4> q;
    for (int i = 10; i < 14; ++i) {
        CHECK(q.add(i));
    }
    CHECK(!q.add(99));            /* 默认 overwrite=false */
    CHECK(q.numElements() == 4);  /* 计数不增长 */
    for (int i = 10; i < 14; ++i) { /* 最老的元素仍在（未被覆盖） */
        int out = -1;
        CHECK(q.pull(&out));
        CHECK(out == i);
    }
}

/* ---------- 用例 5：overwrite=true 时挤掉最老元素 ---------- */
static void case_overwrite_replaces_oldest(void)
{
    RingBufCPP<int, 4> q;
    for (int i = 1; i <= 5; ++i) {
        /* 文档语义（README add()）：返回值 = "当时是否还有空位"，
         * 满且 overwrite=true 时**仍会写入**但返回 false。 */
        bool had_room = q.add(i, true);
        CHECK(had_room == (i <= 4));
    }
    CHECK(q.isFull());
    CHECK(q.numElements() == 4);
    for (int i = 2; i <= 5; ++i) { /* 1 被覆盖，剩下 2..5 */
        int out = -1;
        CHECK(q.pull(&out));
        CHECK(out == i);
    }
}

/* ---------- 用例 6：_head 环绕（跨过数组末尾的多轮回绕） ---------- */
static void case_head_wraparound(void)
{
    RingBufCPP<int, 4> q;
    for (int round = 0; round < 25; ++round) { /* 25 轮 ⇒ _head 绕 6 圈以上 */
        CHECK(q.add(round));
        int out = -1;
        CHECK(q.pull(&out));
        CHECK(out == round);
        CHECK(q.isEmpty());
    }
    /* 再灌满一次，验证环绕后 getTail() 仍指向最老元素 */
    for (int i = 100; i < 104; ++i) {
        CHECK(q.add(i));
    }
    for (int i = 100; i < 104; ++i) {
        int out = -1;
        CHECK(q.pull(&out));
        CHECK(out == i);
    }
}

/* ---------- 用例 7：peek 取值 / 越界返回 NULL / 指针可写 ---------- */
static void case_peek_and_bounds(void)
{
    RingBufCPP<int, 8> q;
    CHECK(q.peek(0) == NULL);       /* 空缓冲 */
    for (int i = 1; i <= 3; ++i) {
        CHECK(q.add(i * 10));
    }
    for (int i = 0; i < 3; ++i) {
        int *p = q.peek(static_cast<size_t>(i));
        CHECK(p != NULL);
        CHECK(*p == (i + 1) * 10);
    }
    CHECK(q.peek(3) == NULL);       /* 越界（numElements=3） */
    CHECK(q.peek(100) == NULL);     /* 远超容量 */
    int *first = q.peek(0);
    CHECK(first != NULL);
    *first = 77;                    /* README：peek 允许直接改内部元素 */
    int out = -1;
    CHECK(q.pull(&out));
    CHECK(out == 77);
}

/* ---------- 用例 8：状态访问器 isEmpty/isFull/numElements ---------- */
static void case_state_accessors(void)
{
    RingBufCPP<int, 3> q;
    CHECK(q.isEmpty());
    CHECK(!q.isFull());
    CHECK(q.numElements() == 0);
    CHECK(q.add(1));
    CHECK(!q.isEmpty());
    CHECK(q.numElements() == 1);
    CHECK(q.add(2));
    CHECK(q.add(3));
    CHECK(q.numElements() == 3);
    CHECK(q.isFull());
    int out = -1;
    CHECK(q.pull(&out));
    CHECK(q.numElements() == 2);
    CHECK(!q.isFull());
    CHECK(q.pull(&out));
    CHECK(q.pull(&out));
    CHECK(q.isEmpty());
    CHECK(q.numElements() == 0);
}

/* ---------- 用例 9：结构体类型深拷贝（模板库支持非平凡对象） ---------- */
struct Sample {
    uint32_t id;
    char tag[8];
    double value;
};

static void case_struct_deep_copy(void)
{
    RingBufCPP<Sample, 4> q;
    Sample s;
    s.id = 0xC0FFEEu;
    std::memset(s.tag, 0, sizeof(s.tag));
    std::memcpy(s.tag, "ring", 5);
    s.value = 3.25;

    CHECK(q.add(s));
    /* 加入后改动源对象：缓冲里必须仍是加入时的快照（深拷贝语义） */
    s.id = 0xDEADu;
    std::memcpy(s.tag, "changed", 8);
    s.value = -1.0;

    Sample out;
    std::memset(&out, 0, sizeof(out));
    CHECK(q.pull(&out));
    CHECK(out.id == 0xC0FFEEu);
    CHECK(std::strcmp(out.tag, "ring") == 0);
    CHECK(out.value == 3.25);
    CHECK(q.isEmpty());
}

/* ---------- 用例 10：容量为 1 的退化边界 ---------- */
static void case_capacity_one_edge(void)
{
    RingBufCPP<uint8_t, 1> q;
    CHECK(q.add(7));
    CHECK(q.isFull());
    CHECK(q.numElements() == 1);
    CHECK(!q.add(8));               /* 满且不覆盖：不写入 */
    CHECK(!q.add(9, true));         /* 返回 false（当时无空位）… */
    CHECK(q.numElements() == 1);    /* …但 overwrite 仍写入了 9 */
    uint8_t out = 0;
    CHECK(q.pull(&out));
    CHECK(out == 9);
    CHECK(q.isEmpty());
    CHECK(!q.pull(&out));
}

/* ---------- 用例 11：静态分配（栈对象、无堆内存、地址落在对象内） ---------- */
static void case_static_allocation_no_heap(void)
{
    RingBufCPP<int, 8> q;
    /* 8 个元素 + 两个 size_t 计数器必须全部内嵌在对象里（编译期静态分配） */
    CHECK(sizeof(RingBufCPP<int, 8>) >= 8 * sizeof(int) + 2 * sizeof(size_t));
    for (int i = 0; i < 8; ++i) {
        CHECK(q.add(i * 3));
    }
    const char *base = reinterpret_cast<const char *>(&q);
    for (size_t i = 0; i < 8; ++i) {
        int *p = q.peek(i);
        CHECK(p != NULL);
        const char *addr = reinterpret_cast<const char *>(p);
        CHECK(addr >= base && addr < base + sizeof(q)); /* 不来自 malloc */
    }
}

/* ---------- 用例 12：RB_ATOMIC 抽象在 OHOS 上已定义且可嵌套 ---------- */
static void case_atomic_macro_defined_nested(void)
{
    int depth = 0;
    RB_ATOMIC_START {
        ++depth;
        RB_ATOMIC_START {
            ++depth;
        }
        RB_ATOMIC_END
    }
    RB_ATOMIC_END
    CHECK(depth == 2);

    /* 宏是编译期抽象：包一层 add/pull 仍必须正常工作 */
    RingBufCPP<int, 4> q;
    RB_ATOMIC_START {
        CHECK(q.add(5));
    }
    RB_ATOMIC_END
    int out = -1;
    RB_ATOMIC_START {
        CHECK(q.pull(&out));
    }
    RB_ATOMIC_END
    CHECK(out == 5);
}

int main(void)
{
    std::printf("=== embedded_ringbuf_cpp 1.3 consumer test (test_package) ===\n");

    RUN(case_add_pull_fifo_order);
    RUN(case_empty_pull_rejected);
    RUN(case_capacity_full_boundary);
    RUN(case_reject_when_full_no_overwrite);
    RUN(case_overwrite_replaces_oldest);
    RUN(case_head_wraparound);
    RUN(case_peek_and_bounds);
    RUN(case_state_accessors);
    RUN(case_struct_deep_copy);
    RUN(case_capacity_one_edge);
    RUN(case_static_allocation_no_heap);
    RUN(case_atomic_macro_defined_nested);

    std::printf("TOTAL cases=%d pass=%d fail=%d assertions=%d assertion_fail=%d\n",
                g_cases, g_cases - g_case_fail, g_case_fail, g_asserts, g_assert_fail);
    if (g_case_fail == 0 && g_assert_fail == 0) {
        std::printf("CONSUMER TEST PASS\n");
        return 0;
    }
    std::printf("CONSUMER TEST FAIL\n");
    return 1;
}
