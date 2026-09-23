// ohos_test.cpp — HarmonyOS 专项测试 for bbhash 1.0.0 (header-only).
//
// 验证三个与 OHOS aarch64 平台相关的真实行为（区别于上游 Bootest 与消费者 test.cpp）：
//   1) 严格编译：本文件在 OHOS clang 工具链下以 -Werror 编译（见 CMakeLists），
//      直接验证上游补丁（#include <sys/types.h> 提供 u_int64_t）在 OHOS 上成立。
//   2) 多线程构造：使用 pthread（OHOS 原生线程）并行构造 minimal perfect hash。
//   3) save/load 往返：序列化到流并重新加载后，lookup 结果与原始一致
//      （覆盖二进制 I/O 在 OHOS 上的字节序/对齐行为）。
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <sstream>
#include <vector>

#include "BooPHF.h"

int main() {
    typedef boomphf::SingleHashFunctor<uint64_t> hasher_t;
    typedef boomphf::mphf<uint64_t, hasher_t> boophf_t;

    const uint64_t N = 200000;
    std::vector<uint64_t> keys;
    keys.reserve(N);
    uint64_t x = 0x2545F4914F6CDD1DULL;
    for (uint64_t i = 0; i < N; ++i) {
        x ^= x << 7; x ^= x >> 9; x ^= x << 8;
        keys.push_back(x);
    }

    // 2) 多线程（pthread）构造
    int nthreads = 4;
    boophf_t* bphf = new boophf_t(keys.size(), keys, nthreads);
    assert(bphf);

    // 原始 lookup 唯一性
    std::vector<uint64_t> idx0(keys.size());
    std::vector<bool> seen0(N, false);
    for (uint64_t i = 0; i < keys.size(); ++i) {
        idx0[i] = bphf->lookup(keys[i]);
        if (idx0[i] >= N || seen0[idx0[i]]) {
            printf("FAIL: initial lookup non-bijective at %llu\n",
                   (unsigned long long)i);
            delete bphf;
            return 1;
        }
        seen0[idx0[i]] = true;
    }

    // 3) save/load 往返（stream 序列化）
    std::stringstream ss;
    bphf->save(ss);
    boophf_t* bphf2 = new boophf_t();
    bphf2->load(ss);
    for (uint64_t i = 0; i < keys.size(); ++i) {
        uint64_t idx = bphf2->lookup(keys[i]);
        if (idx != idx0[i]) {
            printf("FAIL: reload lookup mismatch at %llu (%llu != %llu)\n",
                   (unsigned long long)i, (unsigned long long)idx,
                   (unsigned long long)idx0[i]);
            delete bphf;
            delete bphf2;
            return 1;
        }
    }
    delete bphf;
    delete bphf2;
    printf("bbhash OHOS test PASSED: %llu keys, 4-thread build + save/load roundtrip OK\n",
           (unsigned long long)N);
    return 0;
}