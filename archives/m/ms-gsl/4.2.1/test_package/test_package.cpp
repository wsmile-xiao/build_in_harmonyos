#include <gsl/gsl>

#include <array>
#include <iostream>
#include <vector>

int main()
{
    // gsl::span over contiguous storage: size, indexing and iteration.
    std::array<int, 4> storage{{1, 2, 3, 4}};
    gsl::span<int> values{storage};
    if (values.size() != 4 || gsl::at(values, 2) != 3) return 1;

    int sum = 0;
    for (const int value : values) sum += value;
    if (sum != 10) return 2;

    // gsl::span over a dynamic container, including a subspan.
    std::vector<int> dynamic{5, 6, 7, 8, 9};
    gsl::span<int> dynamic_span{dynamic};
    gsl::span<int> tail = dynamic_span.subspan(3);
    if (tail.size() != 2 || tail[1] != 9) return 3;

    // gsl::not_null with a dereferenceable pointer.
    int answer = 42;
    gsl::not_null<int*> answer_ptr{&answer};
    if (*answer_ptr != gsl::narrow<int>(42L)) return 4;

    // gsl::narrow_cast keeps the value; gsl::narrow validates it.
    if (gsl::narrow_cast<unsigned>(7) != 7u) return 5;
    if (gsl::narrow<long>(values.size()) != 4L) return 6;

    // gsl::finally runs its callable when the scope is left.
    bool cleanup_ran = false;
    {
        auto cleanup = gsl::finally([&cleanup_ran] { cleanup_ran = true; });
        (void) cleanup;
    }
    if (!cleanup_ran) return 7;

    std::cout << "ms-gsl test_package passed" << std::endl;
    return 0;
}
