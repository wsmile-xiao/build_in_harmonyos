// test_package/test_boost1_84_timer.cpp — boost1.84-timer 1.84.0 L1 smoke test.
// Exercises Boost.Timer: cpu_timer start/stop/elapsed, format(), and
// auto_cpu_timer automatic reporting. Linkage against the compiled
// libboost_timer.a is mandatory (cpu_timer::elapsed etc. are defined in
// libs/timer/src/cpu_timer.cpp).
#include <boost/timer/timer.hpp>
#include <chrono>
#include <iostream>
#include <thread>

int main() {
    // 1) cpu_timer: start -> sleep -> elapsed must report a positive wall time.
    boost::timer::cpu_timer t;
    t.start();
    std::this_thread::sleep_for(std::chrono::milliseconds(120));
    t.stop();

    boost::timer::cpu_times const elapsed = t.elapsed();
    if (elapsed.wall <= 0) {
        std::cerr << "timer: wall time not positive: " << elapsed.wall << std::endl;
        return 1;
    }
    std::cout << "cpu_timer: wall = " << elapsed.wall << " ns ("
              << static_cast<double>(elapsed.wall) / 1e9 << " s)" << std::endl;

    // 2) format(): default and custom format strings (code from cpu_timer.cpp).
    std::string const formatted = t.format(3);
    if (formatted.empty()) {
        std::cerr << "timer: format() returned empty string" << std::endl;
        return 1;
    }
    std::cout << "cpu_timer::format(3): " << formatted;

    std::string const custom = boost::timer::format(elapsed, 6, "wall=%w s user=%u s system=%s s\n");
    if (custom.find("wall=") == std::string::npos) {
        std::cerr << "timer: custom format placeholder missing: " << custom << std::endl;
        return 1;
    }
    std::cout << "boost::timer::format(custom): " << custom;

    // 3) auto_cpu_timer: reports automatically on destruction (constructor
    //    and destructor live in auto_timers_construction.cpp).
    {
        boost::timer::auto_cpu_timer auto_t(3, "auto_cpu_timer wall=%w s\n");
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    // 4) is_stopped()/resume() state machine.
    if (!t.is_stopped()) {
        std::cerr << "timer: timer should be stopped after stop()" << std::endl;
        return 1;
    }
    t.resume();
    if (t.is_stopped()) {
        std::cerr << "timer: timer should be running after resume()" << std::endl;
        return 1;
    }
    std::cout << "boost1.84-timer 1.84.0: cpu_timer + auto_cpu_timer OK" << std::endl;
    return 0;
}
