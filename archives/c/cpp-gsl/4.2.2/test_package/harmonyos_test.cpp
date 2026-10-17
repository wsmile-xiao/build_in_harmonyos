#ifndef __OHOS__
#error "This test must be compiled with the HarmonyOS toolchain"
#endif

#include <gsl/gsl>

#include <array>
#include <iostream>

int main()
{
    std::array<int, 5> storage{{2, 4, 6, 8, 10}};
    gsl::span<int> values{storage};

    int sum = 0;
    for (const int value : values) sum += value;

    int sentinel = 30;
    gsl::not_null<int*> sentinel_ptr{&sentinel};
    if (sum != *sentinel_ptr || gsl::at(values, 4) != 10) return 1;

    bool finalized = false;
    {
        auto cleanup = gsl::finally([&finalized] { finalized = true; });
        (void) cleanup;
    }
    if (!finalized || gsl::narrow<int>(values.size()) != 5) return 2;

    std::cout << "HARMONYOS_CPP_GSL_TEST_OK arch=x86_64 sum=" << sum << std::endl;
    return 0;
}
