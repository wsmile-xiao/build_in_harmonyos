// test_package/test_boost_thread.cpp — boost1.84-thread 1.84.0 L1 smoke test.
// Exercises Boost.Thread compiled component: thread creation/join/move,
// thread::id, mutex + condition_variable, future/promise, this_thread APIs.
// BOOST_THREAD_PROVIDES_FUTURE: enable boost::future naming (upstream
// libs/thread/test/Jamfile.v2 defines it for the future test targets).
#define BOOST_THREAD_PROVIDES_FUTURE
#include <boost/thread.hpp>
#include <boost/thread/future.hpp>
#include <iostream>
#include <string>

int main() {
    // 1. Thread creation + join with a computed result
    int result = 0;
    {
        boost::thread worker([&result] {
            for (int i = 1; i <= 10; ++i) {
                result += i;
            }
        });
        worker.join();
    }
    if (result != 55) {
        std::cerr << "thread: sum mismatch, got " << result << std::endl;
        return 1;
    }
    std::cout << "thread: computed 1+..+10 = " << result << " in worker" << std::endl;

    // 2. thread::id
    boost::thread::id main_id = boost::this_thread::get_id();
    boost::thread::id worker_id;
    {
        boost::thread id_probe([&worker_id] {
            worker_id = boost::this_thread::get_id();
        });
        id_probe.join();
    }
    if (worker_id == main_id) {
        std::cerr << "thread: worker id equals main id?!" << std::endl;
        return 1;
    }
    std::cout << "thread: main id " << main_id << " != worker id " << worker_id << std::endl;

    // 3. hardware_concurrency
    unsigned int hc = boost::thread::hardware_concurrency();
    std::cout << "thread: hardware_concurrency = " << hc << std::endl;
    if (hc == 0) {
        std::cerr << "thread: hardware_concurrency returned 0" << std::endl;
        return 1;
    }

    // 4. mutex + condition_variable handshake
    boost::mutex m;
    boost::condition_variable cv;
    bool ready = false;
    {
        boost::thread notifier([&m, &cv, &ready] {
            {
                boost::lock_guard<boost::mutex> lk(m);
                ready = true;
            }
            cv.notify_one();
        });
        boost::unique_lock<boost::mutex> lk(m);
        while (!ready) {
            cv.wait(lk);
        }
        notifier.join();
    }
    if (!ready) {
        std::cerr << "thread: condition handshake failed" << std::endl;
        return 1;
    }
    std::cout << "thread: mutex + condition_variable handshake OK" << std::endl;

    // 5. future/promise round-trip
    boost::promise<std::string> p;
    boost::future<std::string> f = p.get_future();
    {
        boost::thread setter([&p] {
            p.set_value("boost-thread-ok");
        });
        setter.join();
    }
    if (f.get() != "boost-thread-ok") {
        std::cerr << "thread: future value mismatch" << std::endl;
        return 1;
    }
    std::cout << "thread: promise -> future round-trip OK" << std::endl;

    // 6. this_thread::sleep_for (sp_thread_sleep path on OHOS via patch 0001)
    boost::this_thread::sleep_for(boost::chrono::milliseconds(5));
    std::cout << "thread: this_thread::sleep_for OK" << std::endl;

    std::cout << "boost1.84-thread 1.84.0 (BOOST_VERSION=" << BOOST_VERSION
              << ") all checks OK" << std::endl;
    return 0;
}
