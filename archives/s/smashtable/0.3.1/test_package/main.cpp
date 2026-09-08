/**
 *  @brief Consumer test for smashtable 0.3.1.
 *
 *  Instantiates three container families through the installed headers and
 *  asserts observable behaviour: upsert/overwrite, size, contains, lookup with
 *  copy-out, miss callbacks, committed and rolled-back transactions,
 *  erase_range and clear. The partitioned store drives the atomic epoch
 *  vocabulary (atomic_ref) at runtime.
 */
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <utility>

#include <smashtable/locked_store.hpp>
#include <smashtable/monotonic_store.hpp>
#include <smashtable/partitioned_store.hpp>
#include <smashtable/reference_store.hpp>

using namespace ashvardanian::smashtable;

using pair_t = mapping<std::size_t, std::size_t>;
struct pair_compare_t {
    using is_transparent = void;
    using value_type = std::size_t;
    bool operator()(pair_t const &a, pair_t const &b) const noexcept { return a.key < b.key; }
    bool operator()(std::size_t a, pair_t const &b) const noexcept { return a < b.key; }
    bool operator()(pair_t const &a, std::size_t b) const noexcept { return a.key < b; }
    bool operator()(std::size_t a, std::size_t b) const noexcept { return a < b; }
};

static void fail(char const *message) {
    std::fprintf(stderr, "smashtable test_package FAILED: %s\n", message);
    std::abort();
}

#define CHECK(condition, message)     if (!(condition)) fail(message);

using reference_t = reference_store<pair_t, pair_compare_t>;
using partitioned_t = partitioned_store<reference_t>;
using locked_t = locked_store<reference_t>;
using monotonic_t = monotonic_avl_set<pair_t, pair_compare_t>;

static void check_upsert_and_lookup(partitioned_t &container) {
    CHECK(succeeded(container.upsert(pair_t {1, 10})), "upsert {1,10} must succeed");
    CHECK(succeeded(container.upsert(pair_t {2, 20})), "upsert {2,20} must succeed");
    CHECK(succeeded(container.upsert(pair_t {1, 11})), "upsert overwrite {1,11} must succeed");
    CHECK(container.size() == 2, "size must be 2 after two distinct keys");

    auto present = container.contains(std::size_t {1});
    CHECK(present.has_value() && *present, "key 1 must be present after upsert");
    auto absent = container.contains(std::size_t {3});
    CHECK(absent.has_value() && !*absent, "key 3 must be absent");

    pair_t result;
    auto found = container.find(std::size_t {1}, copy_to(result), no_op_t {});
    CHECK(succeeded(found) && result.key == 1 && result.mapped == 11, "lookup of key 1 must see the overwritten value 11");

    std::size_t misses = 0;
    auto missing = container.find(std::size_t {3}, [](pair_t const &) noexcept {}, [&misses]() noexcept { ++misses; });
    CHECK(!failed(missing) && misses == 1, "lookup of key 3 must fire the miss callback exactly once");
}

static void check_transactions(partitioned_t &container) {
    auto transaction = *container.transaction();
    CHECK(succeeded(transaction.upsert(pair_t {7, 70})), "transaction upsert {7,70} must succeed");
    CHECK(succeeded(transaction.stage()), "transaction stage must succeed");
    CHECK(succeeded(transaction.commit()), "transaction commit must succeed");

    pair_t committed;
    auto found = container.find(std::size_t {7}, copy_to(committed), no_op_t {});
    CHECK(succeeded(found) && committed.mapped == 70, "committed value must be visible to readers");

    auto rolled_back = *container.transaction();
    CHECK(succeeded(rolled_back.upsert(pair_t {8, 80})), "transaction upsert {8,80} must succeed");
    CHECK(succeeded(rolled_back.stage()), "transaction stage before rollback must succeed");
    CHECK(succeeded(rolled_back.rollback()), "transaction rollback must succeed");
    auto still_absent = container.contains(std::size_t {8});
    CHECK(still_absent.has_value() && !*still_absent, "rolled-back upsert must stay invisible");
}

static void check_erase_and_clear(partitioned_t &container) {
    std::size_t erased = 0;
    CHECK(succeeded(container.erase_range(std::size_t {0}, std::size_t {10},
                                          [&erased](pair_t const &) noexcept { ++erased; })),
          "erase_range over all keys must succeed");
    CHECK(erased == 3, "erase_range must visit every key in range");
    CHECK(container.size() == 0, "container must be empty after erase_range");
    CHECK(succeeded(container.clear()), "clear must succeed");
    CHECK(container.empty(), "container must stay empty after clear");
}

int main() {
    auto made = partitioned_t::make();
    CHECK(made.has_value(), "partitioned_store::make must succeed");
    auto partitioned = *std::move(made);
    check_upsert_and_lookup(partitioned);
    check_transactions(partitioned);
    check_erase_and_clear(partitioned);

    auto locked_made = locked_t::make();
    CHECK(locked_made.has_value(), "locked_store::make must succeed");
    auto locked = *std::move(locked_made);
    CHECK(succeeded(locked.upsert(pair_t {5, 50})), "locked_store upsert must succeed");
    CHECK(locked.size() == 1, "locked_store size must be 1");
    pair_t locked_result;
    auto locked_found = locked.find(std::size_t {5}, copy_to(locked_result), no_op_t {});
    CHECK(succeeded(locked_found) && locked_result.mapped == 50, "locked_store lookup must see value 50");

    auto avl_made = monotonic_t::make();
    CHECK(avl_made.has_value(), "monotonic_avl_set::make must succeed");
    auto avl = *std::move(avl_made);
    for (std::size_t key = 0; key < 8; ++key) CHECK(succeeded(avl.upsert(pair_t {key, key * 100})), "avl upsert must succeed");
    CHECK(avl.size() == 8, "avl size must be 8 after 8 distinct keys");
    auto avl_present = avl.contains(std::size_t {3});
    CHECK(avl_present.has_value() && *avl_present, "avl must contain key 3");
    CHECK(succeeded(avl.clear()), "avl clear must succeed");
    CHECK(avl.empty(), "avl must be empty after clear");

    std::printf("smashtable test_package: all checks passed\n");
    return 0;
}
