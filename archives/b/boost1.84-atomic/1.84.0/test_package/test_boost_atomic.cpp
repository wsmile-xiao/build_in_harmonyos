// test_package/test_boost_atomic.cpp — boost1.84-atomic 1.84.0 L1 smoke test.
// Exercises the Boost.Atomic component the way a downstream consumer does:
// header-only atomics (atomic/atomic_ref) plus the wait/notify API that
// requires the compiled libboost_atomic (libs/atomic/src/lock_pool.cpp).
#include <boost/atomic.hpp>
#include <boost/atomic/atomic_ref.hpp>
#include <boost/memory_order.hpp>

#include <iostream>
#include <thread>

int main() {
    // 1) Classic header-only atomic<int> API
    boost::atomic<int> counter(0);
    if (!counter.is_lock_free()) {
        std::cerr << "atomic<int> unexpectedly not lock-free on this platform"
                  << std::endl;
        return 1;
    }
    int prev = counter.fetch_add(41, boost::memory_order_release);
    counter.fetch_add(1, boost::memory_order_acquire);
    if (counter.load() != 42 || prev != 0) {
        std::cerr << "atomic counter arithmetic mismatch: " << counter.load()
                  << " (expected 42)" << std::endl;
        return 1;
    }
    std::cout << "atomic<int>: fetch_add -> " << counter.load() << std::endl;

    // 2) atomic_ref<T> API (Boost implementation of the C++20 concept)
    int value = 0;
    boost::atomic_ref<int> ref(value);
    ref.store(7, boost::memory_order_release);
    if (ref.load(boost::memory_order_acquire) != 7) {
        std::cerr << "atomic_ref load/store mismatch" << std::endl;
        return 1;
    }
    ref.fetch_add(1);
    if (ref.load() != 8) {
        std::cerr << "atomic_ref fetch_add mismatch" << std::endl;
        return 1;
    }
    std::cout << "atomic_ref<int>: store/fetch_add OK" << std::endl;

    // 3) wait/notify API — the part that needs the compiled libboost_atomic
    //    (lock_pool.cpp; futex path on OHOS). A worker thread blocks in
    //    wait(old_value) until the main thread stores a new value and calls
    //    notify_all(). Mirrors the upstream wait_test_helpers.hpp pattern.
    boost::atomic<int> flag(0);
    int received = -1;
    std::thread worker([&flag, &received]() {
        // Returns as soon as the observed value differs from 0.
        received = flag.wait(0);
    });
    flag.store(42, boost::memory_order_release);
    flag.notify_all();
    worker.join();
    if (received != 42) {
        std::cerr << "wait/notify round-trip failed: received " << received
                  << " (expected 42)" << std::endl;
        return 1;
    }
    std::cout << "wait/notify: worker woke with value " << received << std::endl;

    // 4) atomic_flag basic op
    boost::atomic_flag f;
    if (f.test_and_set(boost::memory_order_acq_rel)) {
        std::cerr << "atomic_flag initially set (expected clear)" << std::endl;
        return 1;
    }
    f.clear(boost::memory_order_release);
    std::cout << "atomic_flag: test_and_set/clear OK" << std::endl;

    std::cout << "boost1.84-atomic 1.84.0: atomic + atomic_ref + wait/notify + flag OK"
              << std::endl;
    return 0;
}
