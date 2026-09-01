// test_di.cpp — boost-di 1.3.2 consumer smoke test.
// Exercises the real Boost.DI API: di::make_injector, di::bind, injector.create.
// Returns 0 on success, 1 on failure.
#include <boost/di.hpp>

#include <cassert>
#include <memory>

namespace di = boost::di;

struct I {
    virtual ~I() = default;
    virtual int value() const = 0;
};

struct Impl : I {
    int value() const override { return 42; }
};

struct App {
    explicit App(std::unique_ptr<I> i) : i_(std::move(i)) {}
    int run() const { return i_->value(); }

private:
    std::unique_ptr<I> i_;
};

int main() {
    auto injector = di::make_injector(di::bind<I>().to<Impl>());
    auto app = injector.create<std::unique_ptr<App>>();
    const int result = app->run();
    assert(result == 42);
    return result == 42 ? 0 : 1;
}
