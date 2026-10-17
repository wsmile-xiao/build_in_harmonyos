// jthread-lite 0.1.0 — HarmonyOS 专项适配测试
// 验证 nonstd::jthread 在 OHOS aarch64 工具链（clang 15, aarch64-unknown-linux-ohos）上
// 的真实线程语义：析构自动 join（jthread 相对 std::thread 的核心增强）、显式 join/detach、
// swap、get_id 与 hardware_concurrency。全部为真实断言，非空壳测试。
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>

#include <nonstd/jthread.hpp>

static int failures = 0;

#define OHOS_SPEC_CHECK(cond, msg)                                        \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::cerr << "FAIL: " << msg << "  (" << #cond << ")\n";      \
            ++failures;                                                   \
        } else {                                                          \
            std::cout << "PASS: " << msg << "\n";                         \
        }                                                                 \
    } while (0)

int main() {
    std::cout << "jthread-lite " << jthread_lite_VERSION
              << " OHOS-specific test (__cplusplus=" << __cplusplus << ")\n";

    // 1. 默认构造：不可 joinable；get_id 为空 id（std::thread 语义）
    {
        nonstd::jthread thr;
        OHOS_SPEC_CHECK(!thr.joinable(), "default-constructed jthread is not joinable");
        OHOS_SPEC_CHECK(thr.get_id() == std::thread::id{}, "default-constructed jthread has null id");
    }

    // 2. 析构自动 join：函数退出时回调必须已完整执行（jthread 核心增强）
    {
        std::atomic<int> ran{0};
        {
            nonstd::jthread thr{[&ran] { ran.store(1); }};
            OHOS_SPEC_CHECK(thr.joinable(), "thread with callback is joinable");
        }
        OHOS_SPEC_CHECK(ran.load() == 1, "destructor auto-joins before scope exit");
    }

    // 3. 显式 join：带参数回调，join 后返回结果可见
    {
        std::atomic<int> product{0};
        nonstd::jthread thr{[&product](int x, int y) { product.store(x * y); }, 6, 7};
        thr.join();
        OHOS_SPEC_CHECK(product.load() == 42, "explicit join waits for callback result (6*7==42)");
        OHOS_SPEC_CHECK(!thr.joinable(), "after join() thread is not joinable");
    }

    // 4. detach：detach 后不可 joinable，回调最终执行
    {
        std::atomic<int> done{0};
        nonstd::jthread thr{[&done] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            done.store(1);
        }};
        thr.detach();
        OHOS_SPEC_CHECK(!thr.joinable(), "after detach() thread is not joinable");
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        OHOS_SPEC_CHECK(done.load() == 1, "detached callback completes");
    }

    // 5. swap：交换后 id 互换
    {
        nonstd::jthread t1{[]{}};
        nonstd::jthread t2{[]{}};
        const auto id1 = t1.get_id();
        const auto id2 = t2.get_id();
        swap(t1, t2);
        OHOS_SPEC_CHECK(t1.get_id() == id2 && t2.get_id() == id1, "swap exchanges thread ids");
        t1.join();
        t2.join();
    }

    // 6. hardware_concurrency：OHOS 上必须为正数
    {
        const unsigned hc = nonstd::jthread::hardware_concurrency();
        OHOS_SPEC_CHECK(hc >= 1, "hardware_concurrency() >= 1 on OHOS");
        std::cout << "  hardware_concurrency() = " << hc << "\n";
    }

    // 注：stop_source/stop_token 在 jthread-lite 0.1.0 上游为声明 stub
    // （get_token/stop_requested 无实现体，上游测试亦标注 not-implemented），
    // 故本测试不断言 stop 语义，只验证已实现且真实链接的 jthread 线程能力。

    if (failures) {
        std::cerr << "HarmonyOS-specific test FAILED (" << failures << " failures)\n";
        return 1;
    }
    std::cout << "HarmonyOS-specific test PASSED\n";
    return 0;
}