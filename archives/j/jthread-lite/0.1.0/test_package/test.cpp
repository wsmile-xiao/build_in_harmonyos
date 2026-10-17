// test_package — jthread-lite 消费者验证（L1 官方测试）
// 真实包含并使用 <nonstd/jthread.hpp>：验证线程创建、自动 join、
// 显式 join 后结果可见、swap 与 hardware_concurrency。真实断言，非空壳。
#include <atomic>
#include <iostream>

#include <nonstd/jthread.hpp>

int main() {
    int failures = 0;

    // 析构自动 join：作用域退出后回调必须已执行
    {
        std::atomic<int> ran{0};
        {
            nonstd::jthread thr{[&ran] { ran.store(1); }};
            if (!thr.joinable()) { std::cerr << "FAIL: joinable\n"; ++failures; }
        }
        if (ran.load() != 1) { std::cerr << "FAIL: auto-join\n"; ++failures; }
    }

    // 显式 join：带参数回调，结果可见
    {
        std::atomic<int> product{0};
        nonstd::jthread thr{[&product](int x, int y) { product.store(x * y); }, 6, 7};
        thr.join();
        if (product.load() != 42) { std::cerr << "FAIL: join result\n"; ++failures; }
    }

    // swap 交换 id
    {
        nonstd::jthread t1{[]{}};
        nonstd::jthread t2{[]{}};
        const auto id1 = t1.get_id();
        const auto id2 = t2.get_id();
        swap(t1, t2);
        if (t1.get_id() != id2 || t2.get_id() != id1) {
            std::cerr << "FAIL: swap\n"; ++failures;
        }
        t1.join();
        t2.join();
    }

    if (nonstd::jthread::hardware_concurrency() < 1) {
        std::cerr << "FAIL: hardware_concurrency\n"; ++failures;
    }

    if (failures) {
        std::cerr << "test_jthread_lite FAILED (" << failures << ")\n";
        return 1;
    }
    std::cout << "test_jthread_lite PASSED (jthread-lite "
              << jthread_lite_VERSION << ")\n";
    return 0;
}