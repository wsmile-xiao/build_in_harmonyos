#include <iostream>
#include <limits>
#include <stxxl/sorter>
#include <stxxl/vector>

struct IntComparator
{
    bool operator()(const int& a, const int& b) const
    {
        return a < b;
    }
    int min_value() const
    {
        return std::numeric_limits<int>::min();
    }
    int max_value() const
    {
        return std::numeric_limits<int>::max();
    }
};

int main()
{
    stxxl::block_manager::get_instance();

    int passed = 0;

    // Check 1: vector element access.
    {
        typedef stxxl::VECTOR_GENERATOR<unsigned long long>::result vector_type;
        const unsigned long long n = 4096;
        vector_type vec(n);
        for (unsigned long long i = 0; i < vec.size(); ++i)
            vec[i] = static_cast<unsigned long long>(i % 1024);
        unsigned long long sum = 0;
        for (unsigned long long i = 0; i < vec.size(); ++i)
            sum += vec[i];
        unsigned long long expect = (n / 1024) * (1024 * 1023 / 2);
        if (sum != expect) {
            std::cerr << "check1 vector element sum mismatch" << std::endl;
            return 1;
        }
        std::cout << "CHECK 1 passed: vector element access" << std::endl;
        ++passed;
    }

    // Check 2: vector iterator access.
    {
        typedef stxxl::VECTOR_GENERATOR<unsigned long long>::result vector_type;
        const unsigned long long n = 4096;
        vector_type vec(n);
        unsigned long long i = 0;
        for (vector_type::iterator it = vec.begin(); it != vec.end(); ++it, ++i)
            *it = static_cast<unsigned long long>(i % 256);
        unsigned long long sum = 0;
        for (vector_type::const_iterator it = vec.begin(); it != vec.end(); ++it)
            sum += *it;
        unsigned long long expect = (n / 256) * (256 * 255 / 2);
        if (sum != expect) {
            std::cerr << "check2 vector iterator sum mismatch" << std::endl;
            return 1;
        }
        std::cout << "CHECK 2 passed: vector iterator access" << std::endl;
        ++passed;
    }

    // Check 3: vector bufwriter/bufreader.
    {
        typedef stxxl::VECTOR_GENERATOR<unsigned long long>::result vector_type;
        const unsigned long long n = 4096;
        vector_type vec(n);
        {
            vector_type::bufwriter_type writer(vec);
            for (unsigned long long i = 0; i < vec.size(); ++i)
                writer << static_cast<unsigned long long>(i % 128);
            writer.finish();
        }
        unsigned long long sum = 0;
        for (vector_type::bufreader_type reader(vec); !reader.empty(); ++reader)
            sum += *reader;
        unsigned long long expect = (n / 128) * (128 * 127 / 2);
        if (sum != expect) {
            std::cerr << "check3 bufreader sum mismatch" << std::endl;
            return 1;
        }
        std::cout << "CHECK 3 passed: vector bufwriter/bufreader" << std::endl;
        ++passed;
    }

    // Check 4: sorter orders descending input ascending.
    {
        typedef stxxl::sorter<int, IntComparator> sorter_type;
        sorter_type sorter(IntComparator(), 16 * 1024 * 1024);
        for (int i = 500; i > 0; --i)
            sorter.push(i);
        sorter.sort();
        int prev = 0;
        int count = 0;
        while (!sorter.empty()) {
            int v = *sorter;
            if (v < prev) {
                std::cerr << "check4 sorter order broken" << std::endl;
                return 1;
            }
            prev = v;
            ++sorter;
            ++count;
        }
        if (count != 500 || prev != 500) {
            std::cerr << "check4 sorter count mismatch" << std::endl;
            return 1;
        }
        std::cout << "CHECK 4 passed: sorter ordering" << std::endl;
        ++passed;
    }

    // Check 5: vector resize keeps prefix values.
    {
        typedef stxxl::VECTOR_GENERATOR<int, 2, 4, 4096>::result vector_type;
        vector_type vec;
        const int n = 2048;
        vec.resize(n);
        for (int i = 0; i < n; i += 100)
            vec[i] = i;
        for (int i = 0; i < n; i += 100) {
            if (vec[i] != i) {
                std::cerr << "check5 resize value mismatch" << std::endl;
                return 1;
            }
        }
        vec.resize(1, true);
        vec.flush();
        std::cout << "CHECK 5 passed: vector resize" << std::endl;
        ++passed;
    }

    // Check 6: vector size and clear.
    {
        typedef stxxl::VECTOR_GENERATOR<int>::result vector_type;
        vector_type vec(1024);
        if (vec.size() != 1024) {
            std::cerr << "check6 size mismatch" << std::endl;
            return 1;
        }
        vec.clear();
        if (!vec.empty()) {
            std::cerr << "check6 clear failed" << std::endl;
            return 1;
        }
        std::cout << "CHECK 6 passed: vector size and clear" << std::endl;
        ++passed;
    }

    std::cout << "ALL " << passed << " CHECKS PASSED" << std::endl;
    return (passed == 6) ? 0 : 1;
}
