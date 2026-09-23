// test_package/test_boost_fiber.cpp — boost1.84-fiber 1.84.0 L1 功能测试。
// 覆盖：fiber 启动/join（launch::post 与 dispatch 两种策略）、channel
// （buffered/unbuffered 往返）、future/promise/packaged_task、barrier、
// condition_variable、mutex —— 消费 boost1.84-context 的 fcontext 实现
// （libboost_context.a 来自依赖包，验证依赖模式链路）。
#include <boost/fiber/all.hpp>
#include <boost/fiber/barrier.hpp>
#include <boost/fiber/buffered_channel.hpp>
#include <boost/fiber/unbuffered_channel.hpp>
#include <boost/fiber/future.hpp>
#include <boost/fiber/mutex.hpp>
#include <boost/fiber/condition_variable.hpp>
#include <boost/fiber/operations.hpp>  // boost::this_fiber::yield / sleep_for
#include <chrono>
#include <iostream>
#include <string>

namespace fibers = boost::fibers;

int check(bool cond, const char *what) {
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        return 1;
    }
    std::cout << "OK: " << what << std::endl;
    return 0;
}

int main() {
    int failures = 0;

    // 1. fiber 启动与 join（post：惰性调度进就绪队列；值带回验证执行）
    {
        int value = 0;
        fibers::fiber f(fibers::launch::post, [&value] { value = 42; });
        f.join();
        failures += check(value == 42, "fiber launch::post + join");
    }

    // 2. launch::dispatch：立即切换进 fiber 执行后再返回
    {
        int value = 0;
        fibers::fiber f(fibers::launch::dispatch, [&value] { value = 7; });
        f.join();
        failures += check(value == 7, "fiber launch::dispatch + join");
    }

    // 3. fiber 间数据交换（resume/yield 底层经 context fcontext 切换）
    {
        int v1 = 0, v2 = 0;
        fibers::fiber fa(fibers::launch::post, [&] {
            v1 = 1;
            boost::this_fiber::yield();
            v2 += 1;
        });
        fibers::fiber fb(fibers::launch::post, [&] {
            v2 += 2;
            boost::this_fiber::yield();
        });
        fa.join();
        fb.join();
        failures += check(v1 == 1 && v2 == 3, "yield interleave");
    }

    // 4. buffered_channel：容量 2 的通道往返
    {
        fibers::buffered_channel<int> ch(2);
        int got = 0;
        fibers::fiber producer(fibers::launch::post, [&ch] {
            ch.push(11);
            ch.push(22);
            ch.close();
        });
        fibers::fiber consumer(fibers::launch::post, [&ch, &got] {
            int v;
            while (boost::fibers::channel_op_status::success == ch.pop(v)) {
                got += v;
            }
        });
        producer.join();
        consumer.join();
        failures += check(got == 33, "buffered_channel push/pop/close");
    }

    // 5. unbuffered_channel：同步交接
    {
        fibers::unbuffered_channel<std::string> ch;
        std::string msg;
        fibers::fiber sender(fibers::launch::post, [&ch] {
            ch.push("hello");
        });
        fibers::fiber receiver(fibers::launch::post, [&ch, &msg] {
            ch.pop(msg);
        });
        sender.join();
        receiver.join();
        failures += check(msg == "hello", "unbuffered_channel push/pop");
    }

    // 6. future/promise（fiber 内等待）
    {
        fibers::promise<int> p;
        fibers::future<int> fut = p.get_future();
        fibers::fiber setter(fibers::launch::post, [&p] {
            p.set_value(99);
        });
        int v = fut.get();
        setter.join();
        failures += check(v == 99, "promise/future set+get");
    }

    // 7. packaged_task + async
    {
        fibers::packaged_task<int(int)> pt([](int x) { return x * 2; });
        fibers::future<int> fut = pt.get_future();
        fibers::fiber runner(fibers::launch::post,
                             std::move(pt), 21);
        int v = fut.get();
        runner.join();
        failures += check(v == 42, "packaged_task async invoke");
    }

    // 8. barrier：3 fiber 汇合点
    {
        int arrived = 0;
        fibers::barrier b(3);
        auto worker = [&] {
            arrived += 1;
            b.wait();
        };
        fibers::fiber f1(fibers::launch::post, worker);
        fibers::fiber f2(fibers::launch::post, worker);
        arrived += 1;
        b.wait();
        f1.join();
        f2.join();
        failures += check(arrived == 3, "barrier wait (3 parties)");
    }

    // 9. fibers::mutex + condition_variable（fiber 间通知）
    {
        fibers::mutex mtx;
        fibers::condition_variable cv;
        bool ready = false;
        int observed = 0;
        fibers::fiber waiter(fibers::launch::post, [&] {
            std::unique_lock<fibers::mutex> lk(mtx);
            cv.wait(lk, [&] { return ready; });
            observed = 1;
        });
        fibers::fiber signer(fibers::launch::post, [&] {
            {
                std::lock_guard<fibers::mutex> lk(mtx);
                ready = true;
            }
            cv.notify_one();
        });
        waiter.join();
        signer.join();
        failures += check(observed == 1, "mutex + condition_variable notify");
    }

    // 10. this_fiber::sleep_for（调度器定时唤醒路径）
    {
        auto t0 = std::chrono::steady_clock::now();
        boost::this_fiber::sleep_for(std::chrono::milliseconds(50));
        auto dt = std::chrono::duration_cast<std::chrono::milliseconds>(
                      std::chrono::steady_clock::now() - t0)
                      .count();
        failures += check(dt >= 40, "this_fiber::sleep_for(50ms)");
    }

    if (failures == 0) {
        std::cout << "test_boost_fiber: ALL OK" << std::endl;
        return 0;
    }
    std::cout << "test_boost_fiber: " << failures << " FAILURES" << std::endl;
    return 1;
}
