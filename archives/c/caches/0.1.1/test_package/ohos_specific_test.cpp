// ohos_specific_test.cpp — HarmonyOS 专项测试 (caches 0.1.1)
// 覆盖 caches header-only 库在 OHOS (aarch64-linux-ohos, clang 15) 平台
// 的实际调用入口：四类缓存策略实例化 + 并发安全 (mutex 在 OHOS libc++ 下
// 可用性) + 跨策略替换（同一 fixed_sized_cache 模板切换策略模板参数）。
#include <caches/cache.hpp>
#include <caches/cache_policy.hpp>
#include <caches/fifo_cache_policy.hpp>
#include <caches/lfu_cache_policy.hpp>
#include <caches/lru_cache_policy.hpp>

#include <cassert>
#include <iostream>
#include <string>
#include <thread>

namespace ohos_ns {
struct Device {
    int id = 0;
    std::string name;
};
}  // namespace ohos_ns

int main() {
    // 1) 四种策略实例化（template template 参数）
    caches::fixed_sized_cache<int, int, caches::LRUCachePolicy> lru(2);
    caches::fixed_sized_cache<int, int, caches::FIFOCachePolicy> fifo(2);
    caches::fixed_sized_cache<int, int, caches::LFUCachePolicy> lfu(2);
    caches::fixed_sized_cache<int, int, caches::NoCachePolicy> no_policy(2);
    lru.Put(1, 10);
    fifo.Put(1, 10);
    lfu.Put(1, 10);
    no_policy.Put(1, 10);
    assert(*lru.Get(1) == 10);
    assert(*fifo.Get(1) == 10);
    assert(*lfu.Get(1) == 10);

    // 2) 自定义类型 (非模板特化，验证 libstdc++/libc++ 容器在 OHOS 可用)
    caches::fixed_sized_cache<std::string, ohos_ns::Device, caches::LRUCachePolicy> dev_cache(2);
    dev_cache.Put("ohos-device-0", ohos_ns::Device{0, "head"});
    dev_cache.Put("ohos-device-1", ohos_ns::Device{1, "display"});
    assert(dev_cache.Get("ohos-device-0")->name == "head");
    assert(dev_cache.Get("ohos-device-1")->name == "display");
    dev_cache.Put("ohos-device-2", ohos_ns::Device{2, "camera"});
    assert(dev_cache.Size() == 2);
    assert(dev_cache.Get("ohos-device-2")->id == 2);

    // 3) TryGet 不抛异常路径
    auto res = dev_cache.TryGet("missing-key");
    assert(!res.second);
    auto ok = dev_cache.TryGet("ohos-device-2");
    assert(ok.second);
    assert(ok.first->id == 2);

    // 4) 并发读写（验证内部 mutex 在 OHOS 线程模型下可用）
    caches::fixed_sized_cache<int, int, caches::LRUCachePolicy> shared(64);
    std::thread writer([&]() {
        for (int i = 0; i < 100; ++i) {
            shared.Put(i, i * 10);
        }
    });
    int reads = 0;
    std::thread readers([&]() {
        for (int i = 0; i < 100; ++i) {
            auto r = shared.TryGet(i);
            reads += (r.second ? 1 : 0);
        }
    });
    writer.join();
    readers.join();
    assert(shared.Size() == 64);

    std::cout << "OHOS specific caches test PASSED (4 policies / custom type / tryget / threads)"
              << std::endl;
    return 0;
}