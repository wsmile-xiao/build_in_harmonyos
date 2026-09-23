#include <intrusive_shared_ptr/ref_counted.h>
#include <intrusive_shared_ptr/refcnt_ptr.h>

#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <iostream>

#if !defined(__OHOS__)
#error "This test is specific to the OHOS target"
#endif

namespace {

struct node : isptr::ref_counted<node> {
    friend isptr::ref_counted<node>;

    static inline int instances = 0;

    explicit node(int initial) : value(initial) { ++instances; }

    int value;

private:
    ~node() noexcept { --instances; }
};

void require(bool condition, const char *message, int &checks)
{
    ++checks;
    if (!condition) {
        std::cerr << "OHOS check failed: " << message << '\n';
        std::exit(1);
    }
}

} // namespace

int main()
{
    int checks = 0;
    require(sizeof(void *) == 8, "AArch64 pointer width is 64 bits", checks);
    require(
        std::atomic<std::intptr_t>::is_always_lock_free,
        "intptr_t atomics are lock-free",
        checks);

    auto first = isptr::make_refcnt<node>(11);
    auto second = isptr::make_refcnt<node>(22);
    std::atomic<isptr::refcnt_ptr<node>> slot(first);

    auto loaded = slot.load(std::memory_order_acquire);
    require(loaded.get() == first.get(), "atomic load preserves identity", checks);
    require(loaded->value == 11, "atomic load preserves value", checks);

    auto expected = first;
    require(
        slot.compare_exchange_strong(
            expected,
            second,
            std::memory_order_acq_rel,
            std::memory_order_acquire),
        "atomic compare_exchange succeeds",
        checks);
    require(slot.load()->value == 22, "atomic slot contains replacement", checks);

    slot.store({}, std::memory_order_release);
    require(!slot.load(std::memory_order_acquire), "atomic slot can be cleared", checks);
    require(node::instances == 2, "local references retain both nodes", checks);

    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"status\":\"passed\","
                 "\"test\":\"ohos_atomic_api\",\"checks\":"
              << checks << "}\n";
    return 0;
}
