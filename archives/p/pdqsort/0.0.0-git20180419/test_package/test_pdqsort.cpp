// Consumer test for the header-only pdqsort package: include the installed
// header and verify pdqsort/pdqsort_branchless against std::sort on the input
// patterns that the algorithm is designed for.
#include <pdqsort.h>

#include <algorithm>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

static int failures = 0;

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

int main()
{
    printf("pdqsort consumer test\n");

    /* --- basic integer sort matches std::sort ------------------------- */
    {
        std::vector<int> values = { 5, 3, 9, 1, 7, 3, -2, 0, 100, -50 };
        std::vector<int> expected = values;
        std::sort(expected.begin(), expected.end());

        pdqsort(values.begin(), values.end());
        CHECK(values == expected, "pdqsort sorts ints exactly like std::sort");
        CHECK(std::is_sorted(values.begin(), values.end()),
              "pdqsort result is sorted");
    }

    /* --- custom comparator -------------------------------------------- */
    {
        std::vector<int> values = { 3, 1, 4, 1, 5, 9, 2, 6 };
        std::vector<int> expected = values;
        std::sort(expected.begin(), expected.end(), std::greater<int>());

        pdqsort(values.begin(), values.end(), std::greater<int>());
        CHECK(values == expected && std::is_sorted(values.begin(), values.end(),
                                                   std::greater<int>()),
              "pdqsort honours a custom comparator");
    }

    /* --- branchless variant ------------------------------------------- */
    {
        std::vector<int> values;
        for (int i = 0; i < 2000; ++i)
            values.push_back((i * 37) % 199);

        pdqsort_branchless(values.begin(), values.end());
        CHECK(std::is_sorted(values.begin(), values.end()),
              "pdqsort_branchless sorts a 2000 element range");
    }

    /* --- large pseudo-random input (deterministic LCG) ----------------- */
    {
        std::vector<int> values(20000);
        unsigned int state = 12345u;
        for (size_t i = 0; i < values.size(); ++i) {
            state = state * 1103515245u + 12345u;
            values[i] = static_cast<int>((state >> 8) % 100000u) - 50000;
        }
        std::vector<int> expected = values;
        std::sort(expected.begin(), expected.end());

        pdqsort(values.begin(), values.end());
        CHECK(values == expected,
              "pdqsort matches std::sort on 20000 pseudo-random ints");
    }

    /* --- pattern defeating: many equal keys --------------------------- */
    {
        std::vector<int> values(5000, 42);
        pdqsort(values.begin(), values.end());
        CHECK(std::is_sorted(values.begin(), values.end()) &&
              values.front() == 42 && values.back() == 42,
              "pdqsort handles 5000 equal elements");
    }

    /* --- already sorted and reverse sorted ---------------------------- */
    {
        std::vector<int> ascending(1000);
        std::vector<int> descending(1000);
        for (int i = 0; i < 1000; ++i) {
            ascending[i] = i;
            descending[i] = 1000 - i;
        }

        pdqsort(ascending.begin(), ascending.end());
        pdqsort(descending.begin(), descending.end());
        CHECK(std::is_sorted(ascending.begin(), ascending.end()) &&
              std::is_sorted(descending.begin(), descending.end()),
              "pdqsort handles sorted and reverse sorted input");
    }

    /* --- strings ------------------------------------------------------ */
    {
        std::vector<std::string> values = { "pear", "apple", "banana", "apple", "cherry" };
        std::vector<std::string> expected = values;
        std::sort(expected.begin(), expected.end());

        pdqsort(values.begin(), values.end());
        CHECK(values == expected, "pdqsort sorts std::string");
    }

    /* --- empty and single element ranges ------------------------------ */
    {
        std::vector<int> empty;
        std::vector<int> single = { 7 };
        pdqsort(empty.begin(), empty.end());
        pdqsort(single.begin(), single.end());
        CHECK(empty.empty() && single.size() == 1 && single[0] == 7,
              "pdqsort handles empty and single element ranges");
    }

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
