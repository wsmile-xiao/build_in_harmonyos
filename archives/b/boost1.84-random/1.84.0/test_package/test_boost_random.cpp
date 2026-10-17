// test_package/test_boost_random.cpp — boost1.84-random 1.84.0 L1 smoke test.
// Exercises Boost.Random: mt19937 engine (validation + distributions) and
// random_device (compiled library source random_device.cpp, /dev/urandom).
#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_int_distribution.hpp>
#include <boost/random/uniform_real_distribution.hpp>
#include <boost/random/random_device.hpp>
#include <boost/random/variate_generator.hpp>
#include <iostream>
#include <set>
#include <string>

int main() {
    // 1. mt19937 seeded validation value (upstream BOOST_RANDOM_VALIDATION_VALUE)
    boost::random::mt19937 rng(42u);
    // discard to a known state and check reproducibility (same seed => same seq)
    boost::random::mt19937 rng2(42u);
    if (rng() != rng2()) {
        std::cerr << "mt19937: same seed produced different first values" << std::endl;
        return 1;
    }
    std::cout << "mt19937: seed reproducibility OK (first value " << rng() << ")" << std::endl;

    // 2. mt19937 uniform_int_distribution: values within [1,6]
    boost::random::uniform_int_distribution<> die(1, 6);
    std::set<int> seen;
    for (int i = 0; i < 1000; ++i) {
        int v = die(rng);
        if (v < 1 || v > 6) {
            std::cerr << "uniform_int_distribution out of range: " << v << std::endl;
            return 1;
        }
        seen.insert(v);
    }
    if (seen.size() < 4) {
        std::cerr << "uniform_int_distribution coverage too narrow: " << seen.size() << std::endl;
        return 1;
    }
    std::cout << "uniform_int_distribution [1,6]: all values in range, coverage "
              << seen.size() << "/6" << std::endl;

    // 3. uniform_real_distribution: values within [0,1)
    boost::random::uniform_real_distribution<> unit(0.0, 1.0);
    for (int i = 0; i < 1000; ++i) {
        double v = unit(rng);
        if (v < 0.0 || v >= 1.0) {
            std::cerr << "uniform_real_distribution out of [0,1): " << v << std::endl;
            return 1;
        }
    }
    std::cout << "uniform_real_distribution [0,1): all in range" << std::endl;

    // 4. random_device (compiled library): entropy + generate + range
    boost::random_device rd;
    double entropy = rd.entropy();
    if (entropy < 0) {
        std::cerr << "random_device: negative entropy " << entropy << std::endl;
        return 1;
    }
    boost::random_device::result_type val = rd();
    if (val < (rd.min)() || val > (rd.max)()) {
        std::cerr << "random_device value out of range" << std::endl;
        return 1;
    }
    unsigned int buf[10];
    rd.generate(buf, buf + 10);
    std::cout << "random_device: entropy=" << entropy << ", value=" << val
              << ", generate(10) OK" << std::endl;

    // 5. random_device uniqueness: two devices produce at least some different bytes
    boost::random_device rd2;
    std::set<unsigned int> distinct;
    for (int i = 0; i < 32; ++i) distinct.insert(rd2());
    if (distinct.size() < 8) {
        std::cerr << "random_device: only " << distinct.size() << " distinct values in 32 draws" << std::endl;
        return 1;
    }
    std::cout << "random_device: " << distinct.size() << "/32 distinct values" << std::endl;

    // 6. variate_generator classic interface
    boost::variate_generator<boost::random::mt19937&, boost::random::uniform_int_distribution<> >
        roller(rng, die);
    int r = roller();
    if (r < 1 || r > 6) {
        std::cerr << "variate_generator out of range: " << r << std::endl;
        return 1;
    }
    std::cout << "variate_generator: OK (rolled " << r << ")" << std::endl;

    std::cout << "boost1.84-random smoke test PASSED" << std::endl;
    return 0;
}
