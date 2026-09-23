// test_package/test_memtailor.cpp — memtailor 1.4 消费者测试
//
// 六组断言，失败以退出码 2..7 区分。判据全部是**可观测行为**：
// 安装布局（伞头文件 + 三棵头）、Arena 的 LIFO/几何增长/后备内存释放、
// ArenaVector 的 FreeMemory 所有权语义、BufferPool 的 free list 复用与内存核算、
// aarch64 的指针宽度/对齐契约、以及 bionic std::thread 上的每线程分配器可复现性。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

// 伞头文件：上游 install 只发运 include/memtailor/ 一棵目录树，memtailor.h
// 因缺 PUBLIC_HEADER DESTINATION 而漏装（patch 0001 补上）。
#include <memtailor.h>
#include <memtailor/Arena.h>
#include <memtailor/ArenaVector.h>
#include <memtailor/BufferPool.h>

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

// ── 组 1：安装布局 + 版本契约 + C 探测符号 ─────────────────────────────
static int group1() {
    // libmemtailorIsPresent() 是上游唯一放进库里的 extern "C" 符号
    // （configure.ac 的 AC_CHECK_LIB 靠它探测库）；它链接得上就证明
    // -lmemtailor 与静态库归档都是可用的。
    libmemtailorIsPresent();

    const std::string version(MEMTAILOR_VERSION_STRING);
    if (version != "1.4") return fail(2, "MEMTAILOR_VERSION_STRING != \"1.4\"");

    // 三个公开头各自构造一个对象：这一段能编过，本身就说明
    // <memtailor.h>（伞头）、<memtailor/Arena.h>、<memtailor/BufferPool.h>、
    // <memtailor/ArenaVector.h> 都被正确安装到了同一个 include 根下。
    memt::Arena arena;
    memt::BufferPool pool(8);
    memt::ArenaVector<int, false> vec(arena, 4);
    vec.push_back(7);
    if (vec.size() != 1 || *vec.begin() != 7)
        return fail(2, "ArenaVector through <memtailor/ArenaVector.h> is unusable");
    if (pool.getBufferSize() < 8)
        return fail(2, "BufferPool through <memtailor/BufferPool.h> is unusable");

    std::printf("PASS 1: C symbol + MEMTAILOR_VERSION_STRING=\"%s\" + umbrella header "
                "<memtailor.h> and the three public headers all installed\n", version.c_str());
    return 0;
}

// ── 组 2：Arena 的 LIFO / 唯一地址 / 几何增长 / 后备内存释放 ────────────
static int group2() {
    memt::Arena a;

    void* p1 = a.alloc(16);
    void* p2 = a.alloc(32);
    if (p1 == 0 || p2 == 0 || p1 == p2)
        return fail(3, "Arena::alloc returned a null or duplicate address");
    if (!a.fromArena(p1) || !a.fromArena(p2))
        return fail(3, "Arena::fromArena() denied a live allocation");

    // 栈序释放后，同样大小的下一次申请必须拿回同一个地址（LIFO 复用）。
    a.freeTop(p2);
    void* p2b = a.alloc(32);
    if (p2b != p2)
        return fail(3, "Arena did not reuse the freed top allocation (LIFO broken)");

    a.freeTop(p2b);
    a.freeTop(p1);
    if (!a.isEmpty())
        return fail(3, "Arena not empty after every live allocation was freed");

    // size==0 也必须给出**唯一且非空**的地址（Arena.h:55 的文档契约）。
    void* z1 = a.alloc(0);
    void* z2 = a.alloc(0);
    if (z1 == 0 || z2 == 0 || z1 == z2)
        return fail(3, "Arena::alloc(0) gave a null or non-unique address");
    a.freeAllAllocsAndBackingMemory();

    // 几何增长：一次 64KB 申请远超首块（约 16KB），后备内存占用必须上升。
    const size_t before = a.getMemoryUse();
    void* big = a.alloc(64u * 1024u);
    const size_t after = a.getMemoryUse();
    if (big == 0 || after <= before)
        return fail(3, "Arena did not grow its backing blocks for a 64KB request");
    if (!a.fromArena(big))
        return fail(3, "Arena::fromArena() denied an allocation from a grown block");

    a.freeAllAllocsAndBackingMemory();
    if (a.getMemoryUse() != 0 || !a.isEmpty())
        return fail(3, "freeAllAllocsAndBackingMemory() left memory behind");

    std::printf("PASS 2: Arena LIFO reuse + unique zero-size addresses + geometric growth "
                "(%zu -> %zu bytes) + backing-memory release\n", before, after);
    return 0;
}

// ── 组 3：ArenaVector 的 FreeMemory 所有权语义 ─────────────────────────
namespace {
struct Tracker {
    static int live;
    int v;
    explicit Tracker(int x) : v(x) { ++live; }
    Tracker(const Tracker& o) : v(o.v) { ++live; }
    ~Tracker() { --live; }
};
int Tracker::live = 0;
}

static int group3() {
    // (a) ArenaVector<T, true>：析构时把数组那块内存归还给 Arena。
    {
        memt::Arena a;
        {
            memt::ArenaVector<Tracker, true> v(a, 8);
            for (int i = 0; i < 5; ++i) v.push_back(Tracker(i));
            if (v.size() != 5)
                return fail(4, "ArenaVector::size() wrong after push_back");
            if (Tracker::live != 5)
                return fail(4, "ArenaVector did not construct the pushed elements");
            if (a.getAllocatedMemoryUse() == 0)
                return fail(4, "ArenaVector did not take its array from the Arena");
        }
        if (Tracker::live != 0)
            return fail(4, "ArenaVector<...,true> did not destroy its elements");
        if (a.getAllocatedMemoryUse() != 0 || !a.isEmpty())
            return fail(4, "ArenaVector<...,true> did not return its memory to the Arena");
    }

    // (b) ArenaVector<T, false>：元素照样析构，内存留在 Arena 里不还。
    {
        memt::Arena a;
        {
            memt::ArenaVector<Tracker, false> v(a, 8);
            for (int i = 0; i < 3; ++i) v.push_back(Tracker(i));
            v.pop_back();
            if (v.size() != 2)
                return fail(4, "ArenaVector::pop_back() did not shrink the vector");
            v.clear();
            if (!v.empty())
                return fail(4, "ArenaVector::clear() left elements behind");
            if (Tracker::live != 0)
                return fail(4, "pop_back()/clear() did not destroy the elements");
        }
        if (a.getAllocatedMemoryUse() == 0)
            return fail(4, "ArenaVector<...,false> freed memory it was told to keep");
    }

    std::printf("PASS 3: ArenaVector FreeMemory=true reclaims / false retains, "
                "element ctors+dtors balanced in both modes\n");
    return 0;
}

// ── 组 4：BufferPool 的 free list 复用与内存核算 ───────────────────────
static int group4() {
    memt::BufferPool pool(64);

    if (pool.getBufferSize() < 64)
        return fail(5, "BufferPool::getBufferSize() is smaller than requested");
    if (pool.getMemoryUse() != 0)
        return fail(5, "a fresh BufferPool already reports memory use");

    void* a1 = pool.alloc();
    void* a2 = pool.alloc();
    if (a1 == 0 || a2 == 0 || a1 == a2)
        return fail(5, "BufferPool::alloc returned a null or duplicate buffer");
    if (!pool.fromPool(a1) || !pool.fromPool(a2))
        return fail(5, "BufferPool::fromPool() denied a live buffer");
    if (pool.getMemoryUse() < pool.getBufferSize())
        return fail(5, "BufferPool::getMemoryUse() does not account for allocated buffers");

    // free list 复用：free 之后同样大小的下一次 alloc 必须拿回同一块。
    pool.free(a1);
    void* a1b = pool.alloc();
    if (a1b != a1)
        return fail(5, "BufferPool did not reuse the freed buffer (free list broken)");

    pool.freeAllBuffersAndBackingMemory();
    if (pool.getMemoryUse() != 0)
        return fail(5, "freeAllBuffersAndBackingMemory() left backing memory behind");

    // 归还后备内存之后仍必须能继续分配，且新缓冲依然在池的管理范围内。
    void* a3 = pool.alloc();
    if (a3 == 0 || !pool.fromPool(a3))
        return fail(5, "BufferPool could not allocate after releasing its backing memory");

    std::printf("PASS 4: BufferPool free-list reuse + memory accounting + backing-memory "
                "release and re-growth\n");
    return 0;
}

// ── 组 5：鸿蒙特有 A —— aarch64 的指针宽度 / 对齐契约 ───────────────────
static int group5() {
    // memtailor 的对齐契约就是 MemoryAlignment = sizeof(void*)（stdinc.h:101）。
    // aarch64/OHOS 上必须是 8；32 位 ARM 的 OHOS 会是 4。这条断言断的是
    // "平台宽度"，而不是与平台无关的通用功能。
    if (sizeof(void*) != 8)
        return fail(6, "consumer is not a 64-bit build (sizeof(void*) != 8)");
    if (memt::MemoryAlignment != sizeof(void*))
        return fail(6, "memt::MemoryAlignment != sizeof(void*)");

    // Arena：连续 64 次不同大小的申请，每个返回值都必须整除 MemoryAlignment。
    {
        memt::Arena a;
        for (size_t k = 1; k <= 64; ++k) {
            void* p = a.alloc(k);
            if (p == 0)
                return fail(6, "Arena::alloc returned null");
            if (reinterpret_cast<uintptr_t>(p) % memt::MemoryAlignment != 0)
                return fail(6, "Arena::alloc returned a misaligned pointer");
        }
        a.freeAllAllocsAndBackingMemory();
    }

    // BufferPool：实际缓冲尺寸是 align(max(请求值, sizeof(FreeNode)))，aarch64
    // 上 sizeof(FreeNode)==sizeof(void*)==8，所以 BufferPool(1) 的缓冲是 8 字节。
    {
        memt::BufferPool tiny(1);
        if (tiny.getBufferSize() != sizeof(void*))
            return fail(6, "BufferPool(1).getBufferSize() != sizeof(void*) on aarch64");
        for (int i = 0; i < 64; ++i) {
            void* p = tiny.alloc();
            if (p == 0 || reinterpret_cast<uintptr_t>(p) % memt::MemoryAlignment != 0)
                return fail(6, "BufferPool::alloc returned a null or misaligned buffer");
        }
    }

    std::printf("PASS 5: aarch64 contract — MemoryAlignment == sizeof(void*) == %zu, "
                "every Arena/BufferPool pointer %u-byte aligned\n",
                sizeof(void*), memt::MemoryAlignment);
    return 0;
}

// ── 组 6：鸿蒙特有 B —— bionic std::thread 上的每线程分配器可复现性 ─────
namespace {
// memtailor 自身不是线程安全的（文档明示一个 Arena/BufferPool 只给一个线程用），
// 所以每个线程各自持有一份，验证的是"每线程独立的分配器在 OHOS bionic 的
// std::thread + operator new/delete 之下行为逐位可复现"。
//
// 活着的缓冲内容会被复核：若分配器把重叠的地址交给调用方，后写的 tag 会改掉
// 先写的那块，复核立刻失败。地址本身不进校验和，只进对齐判定。
// ok 用 unsigned char 而不是 bool：同一 vector<bool> 的不同下标会挤在同一个
// 字节里，多线程各写一个下标就是 C++ 层面的数据竞争。
void alloc_stress(uint64_t seed, unsigned char* ok, uint64_t* checksum) {
    memt::Arena arena;
    memt::BufferPool pool(64);

    std::vector<void*> buf;          // BufferPool：任意顺序释放
    std::vector<unsigned char> btag;
    std::vector<void*> astack;       // Arena：只能按栈序释放
    std::vector<unsigned char> atag;
    std::vector<size_t> asize;

    uint64_t h = 1469598103934665603ULL;
    uint64_t s = seed;

    for (int i = 0; i < 4000; ++i) {
        s = s * 6364136223846793005ULL + 1442695040888963407ULL;
        const unsigned char t = static_cast<unsigned char>(s & 0xffu);

        if ((s >> 33) & 1u) { // ── BufferPool 分支 ──
            if (buf.size() < 16 && ((s >> 44) & 1u)) {
                void* p = pool.alloc();
                if (p == 0
                    || reinterpret_cast<uintptr_t>(p) % memt::MemoryAlignment != 0) {
                    *ok = 0;
                    return;
                }
                std::memset(p, t, pool.getBufferSize());
                buf.push_back(p);
                btag.push_back(t);
                h = h * 1099511628211ULL + t;
            } else if (!buf.empty()) {
                const size_t j = static_cast<size_t>((s >> 17) % buf.size());
                // 复核：这块缓冲期间没有被另一次分配改写（重叠分配会被这条抓到）。
                if (*static_cast<unsigned char*>(buf[j]) != btag[j]) {
                    *ok = 0;
                    return;
                }
                h = h * 1099511628211ULL + btag[j];
                pool.free(buf[j]);
                buf[j] = buf.back();
                buf.pop_back();
                btag[j] = btag.back();
                btag.pop_back();
            }
        } else { // ── Arena 分支（严格 LIFO）──
            if (astack.size() < 8 && ((s >> 44) & 1u)) {
                const size_t n = static_cast<size_t>((s >> 20) % 97u) + 1u;
                void* p = arena.alloc(n);
                if (p == 0
                    || reinterpret_cast<uintptr_t>(p) % memt::MemoryAlignment != 0) {
                    *ok = 0;
                    return;
                }
                std::memset(p, t, n);
                astack.push_back(p);
                atag.push_back(t);
                asize.push_back(n);
                h = h * 1099511628211ULL + t;
            } else if (!astack.empty()) {
                unsigned char* top = static_cast<unsigned char*>(astack.back());
                if (top[0] != atag.back() || top[asize.back() - 1] != atag.back()) {
                    *ok = 0;
                    return;
                }
                h = h * 1099511628211ULL + atag.back();
                arena.freeTop(astack.back());
                astack.pop_back();
                atag.pop_back();
                asize.pop_back();
            }
        }
    }
    *checksum = h;
}
} // namespace

static int group6() {
    if (std::thread::hardware_concurrency() < 1)
        return fail(7, "std::thread::hardware_concurrency() < 1 on OHOS");

    const int kNThreads = 4;
    std::vector<uint64_t> reference(kNThreads, 0);
    for (int i = 0; i < kNThreads; ++i) {
        unsigned char ok = 1;
        alloc_stress(1000u + static_cast<uint64_t>(i), &ok, &reference[i]);
        if (!ok)
            return fail(7, "single-threaded stress saw a misaligned or clobbered allocation");
    }

    std::vector<uint64_t> parallel(kNThreads, 0);
    std::vector<unsigned char> par_ok(kNThreads, 1);
    std::vector<std::thread> threads;
    for (int i = 0; i < kNThreads; ++i) {
        threads.emplace_back([i, &parallel, &par_ok]() {
            alloc_stress(1000u + static_cast<uint64_t>(i), &par_ok[i], &parallel[i]);
        });
    }
    for (std::thread& th : threads) th.join();

    for (int i = 0; i < kNThreads; ++i) {
        if (!par_ok[i])
            return fail(7, "multi-threaded stress saw a misaligned or clobbered allocation (bionic)");
        if (parallel[i] != reference[i])
            return fail(7, "per-thread allocator result differed from the single-threaded run");
    }

    std::printf("PASS 6: %d bionic std::threads x 4000 alloc/free ops each on private "
                "Arena+BufferPool, checksums identical to the single-threaded reference\n",
                kNThreads);
    return 0;
}

int main() {
    if (const int rc = group1()) return rc;
    if (const int rc = group2()) return rc;
    if (const int rc = group3()) return rc;
    if (const int rc = group4()) return rc;
    if (const int rc = group5()) return rc;
    if (const int rc = group6()) return rc;

    std::printf("ALL PASS: memtailor 1.4 consumer tests (6 groups) on HarmonyOS\n");
    return 0;
}
