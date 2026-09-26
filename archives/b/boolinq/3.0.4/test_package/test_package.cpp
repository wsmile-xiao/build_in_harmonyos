// Consumer test for the packaged boolinq header (R34).
//
// Includes <boolinq/boolinq.h> exactly like a downstream project would
// (packaged include dir only) and runs a chain of real API assertions.
// Checks are counted explicitly and reported; the process exits non-zero on
// any failure (no assert()/NDEBUG pitfalls, nothing is stubbed).
#include <boolinq/boolinq.h>

#include <cstdio>
#include <list>
#include <numeric>
#include <set>
#include <string>
#include <vector>

static int checks = 0;
static int failures = 0;

#define BOOLINQ_CHECK(cond)                                          \
    do {                                                             \
        ++checks;                                                    \
        if (!(cond)) {                                               \
            ++failures;                                              \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__,       \
                         __LINE__, #cond);                           \
        }                                                            \
    } while (0)

int main() {
    using namespace boolinq;

    const std::vector<int> src = {5, 3, 8, 3, 9, 1, 5, 8};

    // 1. from + where + toStdVector
    const std::vector<int> odds =
        from(src).where([](int v) { return v % 2 != 0; }).toStdVector();
    BOOLINQ_CHECK(odds == (std::vector<int>{5, 3, 3, 9, 1, 5}));

    // 2. select
    const std::vector<int> doubled =
        from(src).select([](int v) { return v * 2; }).toStdVector();
    BOOLINQ_CHECK(doubled.size() == src.size());
    BOOLINQ_CHECK(doubled.front() == 10 && doubled.back() == 16);

    // 3. sum / avg
    const int expected_sum = std::accumulate(src.begin(), src.end(), 0);
    BOOLINQ_CHECK(from(src).sum() == expected_sum);
    BOOLINQ_CHECK(from(src).sum() == 42);
    BOOLINQ_CHECK(from(src).avg() == 42 / 8);

    // 4. count / any / all / contains
    BOOLINQ_CHECK(from(src).count() == 8);
    BOOLINQ_CHECK(from(src).any([](int v) { return v > 8; }));
    BOOLINQ_CHECK(!from(src).any([](int v) { return v > 90; }));
    BOOLINQ_CHECK(from(src).all([](int v) { return v > 0; }));
    BOOLINQ_CHECK(from(src).contains(9));

    // 5. first / last / elementAt
    BOOLINQ_CHECK(from(src).first() == 5);
    BOOLINQ_CHECK(from(src).last() == 8);
    BOOLINQ_CHECK(from(src).elementAt(2) == 8);

    // 6. take / skip
    const std::vector<int> head = from(src).take(3).toStdVector();
    BOOLINQ_CHECK(head == (std::vector<int>{5, 3, 8}));
    const std::vector<int> tail = from(src).skip(6).toStdVector();
    BOOLINQ_CHECK(tail == (std::vector<int>{5, 8}));

    // 7. orderBy / distinct
    const std::vector<int> sorted = from(src).orderBy().toStdVector();
    BOOLINQ_CHECK(sorted == (std::vector<int>{1, 3, 3, 5, 5, 8, 8, 9}));
    const std::vector<int> unique = from(src).distinct().toStdVector();
    BOOLINQ_CHECK(unique.size() == 5);

    // 8. toStdSet / toStdList
    const std::set<int> as_set = from(src).toStdSet();
    BOOLINQ_CHECK(as_set.size() == 5);
    const std::list<int> as_list = from(src).toStdList();
    BOOLINQ_CHECK(as_list.size() == 8);

    // 9. append
    const std::vector<int> with_tail =
        from(std::vector<int>{1, 2}).append(3, 4).toStdVector();
    BOOLINQ_CHECK(with_tail == (std::vector<int>{1, 2, 3, 4}));

    // 10. free functions range / repeat
    const std::vector<int> rng = range(0, 10, 2).toStdVector();
    BOOLINQ_CHECK(rng == (std::vector<int>{0, 2, 4, 6, 8}));
    const std::vector<int> rep = repeat(7, 3).toStdVector();
    BOOLINQ_CHECK(rep == (std::vector<int>{7, 7, 7}));

    // 11. non-int element type (std::string pipeline)
    const std::vector<std::string> words = {"harmony", "os", "boolinq", "pc"};
    const std::size_t total_len =
        from(words).select([](const std::string &s) { return s.size(); }).sum();
    BOOLINQ_CHECK(total_len == std::size_t{7 + 2 + 7 + 2});

    // 12. exhausted stream raises LinqEndException (upstream-documented)
    bool caught = false;
    try {
        const std::vector<int> empty;
        from(empty).first();
    } catch (const LinqEndException &) {
        caught = true;
    }
    BOOLINQ_CHECK(caught);

    // 13. for_each drives the pipeline
    int acc = 0;
    from(src).for_each([&](int v) { acc += v; });
    BOOLINQ_CHECK(acc == 42);

    std::printf("boolinq consumer checks: %d run, %d failed\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
