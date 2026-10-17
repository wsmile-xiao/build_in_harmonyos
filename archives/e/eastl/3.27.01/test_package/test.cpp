#include <EASTL/algorithm.h>
#include <EASTL/allocator.h>
#include <EASTL/fixed_string.h>
#include <EASTL/fixed_vector.h>
#include <EASTL/numeric.h>
#include <EASTL/sort.h>
#include <cstddef>
#include <cstdlib>

int main() {
    eastl::fixed_vector<int, 8, false> values;
    values.push_back(9);
    values.push_back(3);
    values.push_back(7);
    values.push_back(1);
    values.push_back(5);

    eastl::sort(values.begin(), values.end());
    const int expected[] = {1, 3, 5, 7, 9};
    if (values.size() != 5)
        return EXIT_FAILURE;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (values[i] != expected[i])
            return EXIT_FAILURE;
    }

    const auto five = eastl::lower_bound(values.begin(), values.end(), 5);
    if (five == values.end() || *five != 5 ||
        eastl::find(values.begin(), values.end(), 8) != values.end())
        return EXIT_FAILURE;
    if (eastl::accumulate(values.begin(), values.end(), 0) != 25)
        return EXIT_FAILURE;

    eastl::fixed_string<char, 16, false> text("Harmony");
    text.append("OS");
    if (text != "HarmonyOS" || text.size() != 9)
        return EXIT_FAILURE;

    // Also exercise an out-of-line symbol from the packaged static library.
    if (eastl::GetDefaultAllocator() == nullptr)
        return EXIT_FAILURE;

    return EXIT_SUCCESS;
}
