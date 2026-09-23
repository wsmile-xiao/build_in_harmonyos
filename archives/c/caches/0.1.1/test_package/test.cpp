// test.cpp — 消费者验证测试 (caches 0.1.1)
// 实际调用 caches::fixed_sized_cache 的 Put/Get/Size/Remove API，
// 验证 header-only 库作为 Conan 依赖在 OHOS 平台可用。
#include <caches/cache.hpp>
#include <caches/fifo_cache_policy.hpp>
#include <caches/lru_cache_policy.hpp>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    using LRU = caches::fixed_sized_cache<std::string, int, caches::LRUCachePolicy>;

    // 1) LRU 基本读写
    LRU cache(3);
    cache.Put("a", 1);
    cache.Put("b", 2);
    cache.Put("c", 3);
    assert(cache.Size() == 3);
    assert(*cache.Get("a") == 1);
    assert(*cache.Get("b") == 2);
    assert(*cache.Get("c") == 3);

    // 2) 容量淘汰：插入第 4 个后最久未用的 "a" 被淘汰
    cache.Put("d", 4);
    assert(cache.Size() == 3);
    bool evicted = false;
    try {
        (void)cache.Get("a");
    } catch (const std::range_error &) {
        evicted = true;
    }
    assert(evicted);
    assert(*cache.Get("d") == 4);

    // 3) Remove
    cache.Remove("b");
    assert(cache.Size() == 2);

    // 4) FIFO 策略同样可用
    using FIFO = caches::fixed_sized_cache<int, int, caches::FIFOCachePolicy>;
    FIFO fifo(2);
    fifo.Put(1, 10);
    fifo.Put(2, 20);
    assert(*fifo.Get(1) == 10);
    assert(*fifo.Get(2) == 20);
    fifo.Put(3, 30);
    assert(fifo.Size() == 2);
    assert(*fifo.Get(3) == 30);

    std::cout << "caches consumer test PASSED (LRU/FIFO Put/Get/Size/Remove)" << std::endl;
    return 0;
}
