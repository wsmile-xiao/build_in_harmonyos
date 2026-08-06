// Range v3 library — consumer test for range-v3/0.12.0
//
// Verifies that range-v3 headers can be included and basic APIs work:
//   - ranges::views::transform
//   - ranges::to_vector
//   - ranges::accumulate
//   - ranges::for_each

#include <cassert>
#include <iostream>
#include <string>
#include <vector>

#include <range/v3/all.hpp>

int main()
{
    // Test 1: views::transform
    std::vector<int> nums = {1, 2, 3, 4, 5};
    auto squares = nums
        | ranges::views::transform([](int x) { return x * x; })
        | ranges::to<std::vector<int>>();
    assert(squares.size() == 5);
    assert(squares[0] == 1);
    assert(squares[2] == 9);
    assert(squares[4] == 25);
    std::cout << "PASS: views::transform — squares OK" << std::endl;

    // Test 2: views::filter
    auto evens = nums
        | ranges::views::filter([](int x) { return x % 2 == 0; })
        | ranges::to<std::vector<int>>();
    assert(evens.size() == 2);
    assert(evens[0] == 2);
    assert(evens[1] == 4);
    std::cout << "PASS: views::filter — evens OK" << std::endl;

    // Test 3: views::take / views::drop
    auto taken = nums | ranges::views::take(3) | ranges::to<std::vector<int>>();
    assert(taken.size() == 3);
    assert(taken[2] == 3);
    auto dropped = nums | ranges::views::drop(2) | ranges::to<std::vector<int>>();
    assert(dropped.size() == 3);
    assert(dropped[0] == 3);
    std::cout << "PASS: views::take / views::drop OK" << std::endl;

    // Test 4: action::push_back (actions)
    std::vector<int> v2;
    ranges::actions::push_back(v2, nums);
    assert(v2.size() == 5);
    std::cout << "PASS: action::push_back OK" << std::endl;

    // Test 5: accumulate
    int sum = ranges::accumulate(nums, 0);
    assert(sum == 15);
    std::cout << "PASS: accumulate — sum=15 OK" << std::endl;

    // Test 6: for_each
    int count = 0;
    ranges::for_each(nums, [&count](int) { ++count; });
    assert(count == 5);
    std::cout << "PASS: for_each — count=5 OK" << std::endl;

    // Test 7: version macro
    assert(RANGE_V3_MAJOR == 0);
    assert(RANGE_V3_MINOR == 12);
    assert(RANGE_V3_PATCHLEVEL == 0);
    std::cout << "PASS: version macros OK ("
              << RANGE_V3_MAJOR << "."
              << RANGE_V3_MINOR << "."
              << RANGE_V3_PATCHLEVEL << ")" << std::endl;

    std::cout << std::endl << "All range-v3 consumer tests PASSED." << std::endl;
    return 0;
}
