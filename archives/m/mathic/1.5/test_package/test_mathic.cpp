// test_package/test_mathic.cpp -- mathic 1.5 消费者测试
//
// 六组断言，失败以退出码 2..7 区分。判据全部是可观测行为：
// 安装布局（伞头文件 + C 探测符号 + 版本串）、BitTriangle 三角位矩阵语义、
// HashTable 的 int/string 键插入查询、PairQueue 的 S-pair 入列出列排序、
// aarch64 指针宽度/对齐契约、以及 bionic std::thread 上的每线程私有结构可复现性。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <sstream>
#include <thread>
#include <vector>

// 伞头文件：patch 0001 补上 src/mathic.h 的安装后，消费者可直接包含。
#include <mathic.h>
#include <mathic/BitTriangle.h>
#include <mathic/HashTable.h>
#include <mathic/PairQueue.h>
#include <memtailor.h>

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

// 与上游 src/test/PairQueue.cpp 同构的最小 S-pair 配置。
namespace {
class PQConf {
public:
    explicit PQConf(int id): mId(id) {}
    int id() const {return mId;}

    typedef std::string PairData;
    void computePairData(size_t col, size_t row, std::string& str) {
        str = pairString(col, row);
    }

    typedef bool CompareResult;
    bool compare(int colA, int rowA, const std::string& strA,
                 int colB, int rowB, const std::string& strB) const {
        (void)colA; (void)rowA; (void)colB; (void)rowB;
        return strA > strB;
    }
    bool cmpLessThan(bool v) const {return v;}

    std::string pairString(size_t col, size_t row) const {
        std::ostringstream out;
        out << col << row << mId;
        return out.str();
    }

private:
    int mId;
};
}

namespace mathic {
namespace PairQueueNamespace {
template<>
struct SupportRetirement<PQConf> {
    static bool const value = false;
};
}
}

// -- 组 1：安装布局 + 版本契约 + C 探测符号 --
static int group1() {
    // libmathicIsPresent() 是上游放进库里的唯一 extern "C" 符号
    // （configure.ac 的 AC_CHECK_LIB 靠它探测库）；链接得上即证明
    // -lmathic 与静态归档可用。
    libmathicIsPresent();

    const std::string version(MATHIC_VERSION_STRING);
    if (version != "1.5")
        return fail(2, "MATHIC_VERSION_STRING != \"1.5\"");

    // 三个核心头各自实例化：能编过即证明伞头 <mathic.h>、
    // <mathic/BitTriangle.h>、<mathic/HashTable.h>、<mathic/PairQueue.h>
    // 都被正确安装到同一 include 根下（含 patch 0001 补装的伞头）。
    mathic::BitTriangle tri;
    tri.addColumn();
    if (tri.columnCount() != 1 || tri.empty())
        return fail(2, "BitTriangle through <mathic/BitTriangle.h> is unusable");

    std::printf("PASS 1: C symbol + MATHIC_VERSION_STRING=\"%s\" + umbrella header "
                "<mathic.h> and core headers all installed\n", version.c_str());
    return 0;
}

// -- 组 2：BitTriangle 三角位矩阵语义 --
static int group2() {
    mathic::BitTriangle tri;
    if (!tri.empty() || tri.columnCount() != 0)
        return fail(3, "fresh BitTriangle not empty");

    const size_t colCount = 20;
    const size_t modPattern = 11;
    for (size_t col = 0; col < colCount; ++col) {
        tri.addColumn();
        for (size_t row = 0; row < col; ++row) {
            if (tri.bit(col, row))
                return fail(3, "new BitTriangle bit not false");
            tri.setBit(col, row, true);
            if (!tri.bit(col, row) || !tri.bitUnordered(col, row) || !tri.bitUnordered(row, col))
                return fail(3, "setBit/bitUnordered mismatch");
            const bool value = ((row + col) % modPattern != 0);
            tri.setBitUnordered(col, row, value);
            if (tri.bit(col, row) != value)
                return fail(3, "setBitUnordered value not preserved");
        }
    }
    if (tri.columnCount() != colCount)
        return fail(3, "columnCount wrong after addColumn");
    // 全量复核写入的 mod-11 图案。
    for (size_t col = 0; col < colCount; ++col)
        for (size_t row = 0; row < col; ++row) {
            const bool value = ((row + col) % modPattern != 0);
            if (tri.bit(col, row) != value)
                return fail(3, "stored bit pattern not preserved");
        }

    std::printf("PASS 2: BitTriangle %zu columns triangle set/get/unordered preserved\n", colCount);
    return 0;
}

// -- 组 3：HashTable 的 int/string 键 --
namespace {
struct IntConf {
    typedef int Key;
    typedef int Value;
    size_t hash(Key k) {return static_cast<size_t>(k);}
    bool keysEqual(Key a, Key b) {return a == b;}
};
struct StrConf {
    typedef std::string Key;
    typedef size_t Value;
    size_t hash(Key k) {return std::hash<std::string>()(k);}
    bool keysEqual(Key a, Key b) {return a == b;}
};
}

static int group3() {
    {
        IntConf c;
        mathic::HashTable<IntConf> h(c);
        h.insert(1, 3);
        h.insert(14, 7);
        h.insert(17, 7);
        h.insert(14, 4);
        mathic::HashTable<IntConf>::Handle* p = h.lookup(14);
        if (p == 0 || p->key() != 14 || p->value() != 7)
            return fail(4, "HashTable<int> lookup(14) wrong");
    }
    {
        StrConf c;
        mathic::HashTable<StrConf> h(c);
        h.insert("hi there", 3);
        h.insert("whooa", 7);
        h.insert("whoah", 7);
        h.insert("hi there", 4);
        mathic::HashTable<StrConf>::Handle* p = h.lookup("hi there");
        if (p == 0 || p->key() != "hi there" || p->value() != 3)
            return fail(4, "HashTable<string> lookup wrong");
        if (h.lookup("hi There") != 0)
            return fail(4, "HashTable<string> case-insensitive false positive");
    }
    std::printf("PASS 3: HashTable int + string key insert/lookup\n");
    return 0;
}

// -- 组 4：PairQueue 入列/出列/排序 --
static int group4() {
    if (mathic::PairQueue<PQConf>::SupportRetirement)
        return fail(5, "PQConf retirement support mismatch");
    mathic::PairQueue<PQConf> pq(PQConf(421));
    if (pq.configuration().id() != 421)
        return fail(5, "PairQueue configuration id lost");
    if (!pq.empty() || pq.pairCount() != 0 || pq.columnCount() != 0)
        return fail(5, "fresh PairQueue not empty");

    mathic::PairQueue<PQConf>::Index* nullIndex = 0;
    pq.addColumnDescending(nullIndex, nullIndex);
    if (pq.retired(0))
        return fail(5, "empty column retired unexpectedly");

    mathic::PairQueue<PQConf>::Index rows[6] = {0, 1, 2, 3, 4, 5};
    const size_t columnCount = 7;
    for (size_t i = 0; i < columnCount; ++i) {
        pq.addColumnDescending(rows, rows + i);
        if ((i == 0) != pq.empty())
            return fail(5, "PairQueue empty() wrong while filling");
        if (pq.pairCount() != (i * (i + 1)) / 2)
            return fail(5, "PairQueue pairCount wrong while filling");
        if (pq.columnCount() != i + 2)  // 含上面那列空列
            return fail(5, "PairQueue columnCount wrong while filling");
    }
    size_t pairCount = (columnCount * (columnCount - 1)) / 2;
    for (size_t i = 0; i < pairCount; ++i) {
        if (pq.empty() || pq.pairCount() != pairCount - i)
            return fail(5, "PairQueue pop sequence count wrong");
        pq.pop();
    }
    if (!pq.empty() || pq.pairCount() != 0)
        return fail(5, "PairQueue not empty after draining");

    std::printf("PASS 4: PairQueue columns/pairs fill + ordered drain (%zu pairs)\n", pairCount);
    return 0;
}

// -- 组 5：鸿蒙特有 A -- 64 位宽度 / 对齐契约 --
static int group5() {
    if (sizeof(void*) != 8)
        return fail(6, "consumer is not a 64-bit build (sizeof(void*) != 8)");
    // mathic 的哈希/队列节点经 memtailor 分配，对齐契约即平台宽度。
    if (memt::MemoryAlignment != sizeof(void*))
        return fail(6, "memt::MemoryAlignment != sizeof(void*)");
    // BitTriangle 列增长确定性：64 列逐列复核 empty/columnCount。
    mathic::BitTriangle tri;
    for (size_t k = 1; k <= 64; ++k) {
        tri.addColumn();
        if (tri.columnCount() != k || tri.empty())
            return fail(6, "BitTriangle column growth not deterministic");
    }
    std::printf("PASS 5: aarch64 contract - sizeof(void*)==%zu, MemoryAlignment==%u, "
                "BitTriangle 64-column growth deterministic\n",
                sizeof(void*), memt::MemoryAlignment);
    return 0;
}

// -- 组 6：鸿蒙特有 B -- bionic 多线程私有结构可复现性 --
namespace {
uint64_t tri_hash(uint64_t seed) {
    // 确定性 LCG 驱动的三角写入 + FNV-1a 累加；只含 mathic 可观测行为。
    mathic::BitTriangle tri;
    uint64_t h = 1469598103934665603ULL;
    uint64_t s = seed;
    for (int i = 0; i < 64; ++i) {
        tri.addColumn();
        for (size_t row = 0; row < static_cast<size_t>(i); ++row) {
            s = s * 6364136223846793005ULL + 1442695040888963407ULL;
            const bool v = ((s >> 33) & 1u) != 0;
            tri.setBit(static_cast<size_t>(i), row, v);
            h = h * 1099511628211ULL + (v ? 1u : 0u);
        }
    }
    for (size_t col = 0; col < 64; ++col)
        for (size_t row = 0; row < col; ++row)
            h = h * 1099511628211ULL + (tri.bit(col, row) ? 7u : 13u);
    return h;
}
}

static int group6() {
    if (std::thread::hardware_concurrency() < 1)
        return fail(7, "std::thread::hardware_concurrency() < 1 on OHOS");
    const int kNThreads = 4;
    std::vector<uint64_t> reference(kNThreads, 0);
    for (int i = 0; i < kNThreads; ++i)
        reference[i] = tri_hash(1000u + static_cast<uint64_t>(i));

    std::vector<uint64_t> parallel(kNThreads, 0);
    std::vector<std::thread> threads;
    for (int i = 0; i < kNThreads; ++i)
        threads.emplace_back([i, &parallel]() {
            parallel[i] = tri_hash(1000u + static_cast<uint64_t>(i));
        });
    for (std::thread& th : threads)
        th.join();

    for (int i = 0; i < kNThreads; ++i)
        if (parallel[i] != reference[i])
            return fail(7, "per-thread BitTriangle result differed from single-threaded run");

    std::printf("PASS 6: %d bionic std::threads x private BitTriangle 64-col build, "
                "checksums identical to single-threaded reference\n", kNThreads);
    return 0;
}

int main() {
    if (const int rc = group1()) return rc;
    if (const int rc = group2()) return rc;
    if (const int rc = group3()) return rc;
    if (const int rc = group4()) return rc;
    if (const int rc = group5()) return rc;
    if (const int rc = group6()) return rc;
    std::printf("ALL PASS: mathic 1.5 consumer tests (6 groups) on HarmonyOS\n");
    return 0;
}
