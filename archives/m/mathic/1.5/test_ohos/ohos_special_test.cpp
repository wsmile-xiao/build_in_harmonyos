// test_ohos/ohos_special_test.cpp — mathic 1.5 HarmonyOS 专项验证
//
// 区别于上游 gtest 套件与 test_package 消费者用例：本测试直接验证
// OHOS aarch64 平台上的适配契约（鸿蒙专项，非上游复述）：
//   S1  aarch64 指针宽度与 memtailor 对齐契约：sizeof(void*)==8，
//       memt::MemoryAlignment==8，mathic 数据结构按平台宽度分配；
//   S2  OHOS bionic 运行时线程确定性：多个 std::thread 各持私有
//       mathic::BitTriangle 做确定性 LCG 写入，校验和与单线程参考
//       逐位一致（验证无隐藏全局共享状态 / 数据竞争）；
//   S3  版本契约：MATHIC_VERSION_STRING=="1.5"（patch 0001 安装伞头后
//       消费者可包含 <mathic.h>）。
// 仅通过已安装公开头与静态库（-lmathic -lmemtailor）编译链接运行。
#include <cstdint>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

#include <mathic.h>
#include <mathic/BitTriangle.h>
#include <memtailor.h>

static int fail(int code, const char* what) {
    std::printf("OHOS-SPECIAL-FAIL[%d]: %s\n", code, what);
    return code;
}

static uint64_t tri_hash(uint64_t seed) {
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

int main() {
    // S1: aarch64 宽度/对齐契约
    if (sizeof(void*) != 8)
        return fail(1, "sizeof(void*) != 8 (not a 64-bit build)");
    if (memt::MemoryAlignment != sizeof(void*))
        return fail(1, "memt::MemoryAlignment != sizeof(void*)");
    std::printf("OHOS-SPECIAL-S1: aarch64 contract OK (sizeof(void*)=%zu, MemoryAlignment=%u)\n",
                sizeof(void*), memt::MemoryAlignment);

    // S3: 版本契约
    const std::string version(MATHIC_VERSION_STRING);
    if (version != "1.5")
        return fail(3, "MATHIC_VERSION_STRING != \"1.5\"");
    std::printf("OHOS-SPECIAL-S3: version contract OK (MATHIC_VERSION_STRING=\"%s\")\n",
                version.c_str());

    // S2: bionic 多线程确定性
    const int kNThreads = 4;
    std::vector<uint64_t> reference(kNThreads, 0);
    for (int i = 0; i < kNThreads; ++i)
        reference[i] = tri_hash(9000u + static_cast<uint64_t>(i));
    std::vector<uint64_t> parallel(kNThreads, 0);
    std::vector<std::thread> threads;
    for (int i = 0; i < kNThreads; ++i)
        threads.emplace_back([i, &parallel]() { parallel[i] = tri_hash(9000u + static_cast<uint64_t>(i)); });
    for (std::thread& th : threads)
        th.join();
    for (int i = 0; i < kNThreads; ++i)
        if (parallel[i] != reference[i])
            return fail(2, "per-thread result differed from single-threaded reference");
    std::printf("OHOS-SPECIAL-S2: %d bionic std::threads x private BitTriangle, checksums identical\n", kNThreads);

    std::printf("OHOS-SPECIAL-ALL-PASS: mathic 1.5 HarmonyOS special test (S1/S2/S3) passed\n");
    return 0;
}
