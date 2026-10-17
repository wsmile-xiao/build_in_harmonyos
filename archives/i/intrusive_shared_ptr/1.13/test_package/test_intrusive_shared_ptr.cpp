#include <intrusive_shared_ptr/ref_counted.h>
#include <intrusive_shared_ptr/refcnt_ptr.h>

#include <cstdlib>
#include <iostream>

namespace {

struct widget : isptr::weak_ref_counted<widget> {
    friend isptr::ref_counted<
        widget,
        isptr::ref_counted_flags::provide_weak_references>;

    static inline int instances = 0;

    explicit widget(int initial) : value(initial) { ++instances; }

    int value;

private:
    ~widget() noexcept { --instances; }
};

void require(bool condition, const char *message, int &checks)
{
    ++checks;
    if (!condition) {
        std::cerr << "check failed: " << message << '\n';
        std::exit(1);
    }
}

} // namespace

int main()
{
    int checks = 0;
    auto owner = isptr::make_refcnt<widget>(42);
    require(static_cast<bool>(owner), "make_refcnt returns a pointer", checks);
    require(owner->value == 42, "pointee value is preserved", checks);
    require(widget::instances == 1, "one pointee is alive", checks);

    auto copy = owner;
    require(copy.get() == owner.get(), "copy shares the pointee", checks);
    require(widget::instances == 1, "copy does not clone the pointee", checks);

    auto weak = owner->get_weak_ptr();
    require(static_cast<bool>(weak), "weak reference is created", checks);
    auto locked = weak->lock();
    require(locked.get() == owner.get(), "weak reference locks while alive", checks);
    require(locked->value == 42, "locked pointer exposes the value", checks);

    owner.reset();
    copy.reset();
    require(widget::instances == 1, "locked pointer retains the pointee", checks);
    locked.reset();
    require(widget::instances == 0, "last strong pointer destroys the pointee", checks);

    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"status\":\"passed\","
                 "\"test\":\"consumer_api\",\"checks\":"
              << checks << "}\n";
    return 0;
}
