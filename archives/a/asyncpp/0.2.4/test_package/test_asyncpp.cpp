// test_asyncpp.cpp — asyncpp 0.2.4 消费者测试（鸿蒙特有测试行）
//
// 一个 TU 一次性包含全部 23 个公开头（消费端最坏包含形态，同时充当头文件自包含
// 检查），随后对 task/generator/event/mutex/shared_mutex/semaphore/sleep/rc_ptr
// 逐条断言。CHECK 宏自计数，任一失败即非零退出；断言总数由程序自报。
//
// 末段显式调用 asyncpp::testing::path::dump()：该函数定义在 src/testing/
// interleaver.o（std::format 所在目标），会把 libc++experimental.a 拉进链接，
// 用于验证 package_info 下发的 c++experimental 链接口对消费者真实可用。
#include <asyncpp/concepts.hpp>
#include <asyncpp/container/atomic_collection.hpp>
#include <asyncpp/container/atomic_deque.hpp>
#include <asyncpp/container/atomic_item.hpp>
#include <asyncpp/container/atomic_stack.hpp>
#include <asyncpp/event.hpp>
#include <asyncpp/generator.hpp>
#include <asyncpp/join.hpp>
#include <asyncpp/lock.hpp>
#include <asyncpp/memory/rc_ptr.hpp>
#include <asyncpp/mutex.hpp>
#include <asyncpp/promise.hpp>
#include <asyncpp/scheduler.hpp>
#include <asyncpp/semaphore.hpp>
#include <asyncpp/shared_mutex.hpp>
#include <asyncpp/sleep.hpp>
#include <asyncpp/stream.hpp>
#include <asyncpp/task.hpp>
#include <asyncpp/testing/interleaver.hpp>
#include <asyncpp/testing/suspension_point.hpp>
#include <asyncpp/thread_pool.hpp>
#include <asyncpp/threading/cache.hpp>
#include <asyncpp/threading/spinlock.hpp>

#include <chrono>
#include <cstdio>
#include <vector>

using namespace asyncpp;
using namespace std::chrono_literals;

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                          \
    do {                                                     \
        ++g_checks;                                          \
        if (!(cond)) {                                       \
            ++g_failed;                                      \
            std::printf("FAIL[%d]: %s\n", g_checks, #cond);  \
        }                                                    \
    } while (false)

static task<int> sum_task(int n) {
    int sum = 0;
    for (int i = 1; i <= n; ++i) {
        sum += i;
    }
    co_return sum;
}

struct managed : rc_from_this {
    void destroy() {
        ++destroyed;
    }
    size_t destroyed = 0;
};

int main() {
    // ── 1. 线程池调度 + 协程任务 ────────────────────────────────────────
    thread_pool pool(2);
    auto pooled = launch(sum_task(10), pool);
    CHECK(join(pooled) == 55);

    // ── 2. 默认（内联）调度器 ──────────────────────────────────────────
    auto inline_task = launch(sum_task(4));
    CHECK(join(inline_task) == 10);

    // ── 3. generator 惰性序列 ──────────────────────────────────────────
    const auto numbers = [](int count) -> generator<int> {
        for (int i = 0; i < count; ++i) {
            co_yield i;
        }
    }(4);
    const std::vector<int> values{std::begin(numbers), std::end(numbers)};
    CHECK(values.size() == 4);
    CHECK(values == (std::vector<int>{ 0, 1, 2, 3 }));

    // ── 4. event 一次性取值 ────────────────────────────────────────────
    event<int> evt;
    CHECK(evt._debug_get_result().has_value() == false);
    evt.set_value(1);
    CHECK(evt._debug_get_result().get_or_throw() == 1);

    // ── 5. mutex 互斥语义 ──────────────────────────────────────────────
    mutex mtx;
    CHECK(mtx.try_lock());
    CHECK(mtx.try_lock() == false);
    mtx.unlock();
    CHECK(mtx.try_lock());
    mtx.unlock();
    CHECK(mtx._debug_is_locked() == false);

    // ── 6. shared_mutex 排他/共享语义 ──────────────────────────────────
    shared_mutex smtx;
    CHECK(smtx.try_lock());
    CHECK(smtx.try_lock_shared() == false);
    smtx.unlock();
    CHECK(smtx.try_lock_shared());
    smtx.unlock_shared();
    CHECK(smtx.try_lock());
    smtx.unlock();

    // ── 7. counting_semaphore 计数语义 ─────────────────────────────────
    counting_semaphore sema(1);
    CHECK(sema.try_acquire());
    CHECK(sema.try_acquire() == false);
    sema.release();
    CHECK(sema.try_acquire());
    sema.release();

    // ── 8. sleep_for / sleep_until 时序 ────────────────────────────────
    const auto start = std::chrono::steady_clock::now();
    join(sleep_for(5ms));
    CHECK(std::chrono::steady_clock::now() - start >= 5ms);
    join(sleep_until(std::chrono::steady_clock::now() + 2ms));
    CHECK(std::chrono::steady_clock::now() - start >= 7ms);

    // ── 9. rc_ptr 引用计数 ─────────────────────────────────────────────
    {
        managed object;
        {
            rc_ptr<managed> ptr(&object);
            CHECK(static_cast<bool>(ptr));
            CHECK(ptr.use_count() == 1);
            CHECK(ptr.unique());
            CHECK(ptr.get() == &object);
        }
        CHECK(object.destroyed == 1);
    }

    // ── 10. testing 模块链接（std::format → libc++experimental） ────────
    testing::path empty_path;
    CHECK(empty_path.dump().empty());

    std::printf("asyncpp consumer checks: %d run, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
