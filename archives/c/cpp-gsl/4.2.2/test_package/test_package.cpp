#include <gsl/gsl>

#include <array>
#include <iostream>

int main()
{
    std::array<int, 4> storage{{1, 2, 3, 4}};
    gsl::span<int> values{storage};
    if (values.size() != 4 || gsl::at(values, 2) != 3) return 1;

    int answer = 42;
    gsl::not_null<int*> answer_ptr{&answer};
    if (*answer_ptr != gsl::narrow<int>(42L)) return 2;

    bool cleanup_ran = false;
    {
        auto cleanup = gsl::finally([&cleanup_ran] { cleanup_ran = true; });
        (void) cleanup;
    }
    if (!cleanup_ran) return 3;

    std::cout << "cpp-gsl test_package passed" << std::endl;
    return 0;
}
