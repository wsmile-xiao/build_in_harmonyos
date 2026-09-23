// test_package/test_boost_chrono.cpp — boost1.84-chrono 1.84.0 L1 smoke test.
// Exercises Boost.Chrono: steady_clock / system_clock / high_resolution_clock
// now(), duration arithmetic + casts, time_point arithmetic, thread_clock.
#include <boost/chrono/chrono.hpp>
#include <boost/chrono/chrono_io.hpp>
#include <boost/chrono/thread_clock.hpp>
#include <boost/chrono/process_cpu_clocks.hpp>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    // 1. steady_clock: now() must be non-decreasing across two calls
    boost::chrono::steady_clock::time_point t1 = boost::chrono::steady_clock::now();
    boost::chrono::steady_clock::time_point t2 = boost::chrono::steady_clock::now();
    if (t2 < t1) {
        std::cerr << "steady_clock: time went backwards" << std::endl;
        return 1;
    }
    std::cout << "steady_clock: is_steady=" << boost::chrono::steady_clock::is_steady
              << ", elapsed=" << boost::chrono::duration_cast<boost::chrono::nanoseconds>(t2 - t1).count()
              << "ns" << std::endl;

    // 2. duration arithmetic: 3s + 500ms == 3500ms
    boost::chrono::seconds s(3);
    boost::chrono::milliseconds ms(500);
    boost::chrono::milliseconds total = boost::chrono::duration_cast<boost::chrono::milliseconds>(s + ms);
    if (total.count() != 3500) {
        std::cerr << "duration arithmetic: expected 3500ms, got " << total.count() << "ms" << std::endl;
        return 1;
    }
    std::cout << "duration: 3s + 500ms = " << total.count() << "ms" << std::endl;

    // 3. duration_cast: 1001ms -> 1s
    boost::chrono::milliseconds big(1001);
    if (boost::chrono::duration_cast<boost::chrono::seconds>(big).count() != 1) {
        std::cerr << "duration_cast: 1001ms != 1s" << std::endl;
        return 1;
    }

    // 4. system_clock::time_point arithmetic: now() + 1s > now()
    boost::chrono::system_clock::time_point now = boost::chrono::system_clock::now();
    boost::chrono::system_clock::time_point later = now + boost::chrono::seconds(1);
    if (!(later > now)) {
        std::cerr << "time_point arithmetic failed" << std::endl;
        return 1;
    }
    std::cout << "system_clock: now + 1s > now OK" << std::endl;

    // 5. thread_clock (compiled library source thread_clock.cpp)
    boost::chrono::thread_clock::time_point tc_start = boost::chrono::thread_clock::now();
    volatile int sink = 0;
    for (int i = 0; i < 1000000; ++i) sink += i;
    boost::chrono::thread_clock::time_point tc_end = boost::chrono::thread_clock::now();
    boost::chrono::nanoseconds cpu_ns = boost::chrono::duration_cast<boost::chrono::nanoseconds>(tc_end - tc_start);
    std::cout << "thread_clock: consumed " << cpu_ns.count() << "ns CPU" << std::endl;

    // 6. process_cpu_clocks (compiled library source process_cpu_clocks.cpp)
    typedef boost::chrono::process_cpu_clock clock_type;
    clock_type::time_point cstart = clock_type::now();
    clock_type::time_point cend = clock_type::now();
    // process_cpu_clock 的 duration rep 是 process_times{real,user,system}
    if (!(cend.time_since_epoch().count().real >= cstart.time_since_epoch().count().real)) {
        std::cerr << "process_cpu_clocks: real time went backwards" << std::endl;
        return 1;
    }
    std::cout << "process_cpu_clocks: real elapsed "
              << (cend.time_since_epoch().count().real - cstart.time_since_epoch().count().real)
              << "ns" << std::endl;

    // 7. duration I/O (chrono_io)
    std::stringstream ss;
    ss << boost::chrono::milliseconds(1500);
    std::string out = ss.str();
    if (out.empty()) {
        std::cerr << "duration output empty" << std::endl;
        return 1;
    }
    std::cout << "duration I/O: " << out << std::endl;

    std::cout << "boost1.84-chrono smoke test PASSED" << std::endl;
    return 0;
}

