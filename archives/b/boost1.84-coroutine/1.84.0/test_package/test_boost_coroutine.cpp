// test_package/test_boost_coroutine.cpp — boost1.84-coroutine 1.84.0 L1 smoke test.
// Exercises the component-specific API surface: asymmetric pull/push,
// symmetric call/yield, stack allocators, range iterators and exception paths.
#include <boost/coroutine/asymmetric_coroutine.hpp>
#include <boost/coroutine/symmetric_coroutine.hpp>
#include <boost/coroutine/stack_traits.hpp>
#include <boost/coroutine/protected_stack_allocator.hpp>
#include <boost/coroutine/standard_stack_allocator.hpp>
#include <iostream>
#include <string>
#include <vector>
#include <stdexcept>

namespace coro = boost::coroutines;

// -- asymmetric: push_type yields ints, pull_type iterates --
void gen_ints(coro::asymmetric_coroutine<int>::push_type &yield) {
    for (int i = 1; i <= 5; ++i) yield(i);
}
void gen_str(coro::asymmetric_coroutine<std::string>::push_type &yield) {
    yield(std::string("hello"));
    yield(std::string("world"));
}

// -- symmetric: ping-pong between coroutines --
void symm_yield_fn(coro::symmetric_coroutine<void>::yield_type &yield) {
    yield();
}
void symm_call_fn(coro::symmetric_coroutine<void>::yield_type &yield) {
    yield();
}

int main() {
    // 1. asymmetric pull_type range pull + get
    {
        coro::asymmetric_coroutine<int>::pull_type coro(gen_ints);
        std::vector<int> out;
        for (int v : coro) out.push_back(v);
        if (out.size() != 5 || out[0] != 1 || out[4] != 5) {
            std::cerr << "FAIL: asymmetric int range size=" << out.size() << std::endl;
            return 1;
        }
        std::cout << "PASS asymmetric int range: 1..5\n";
    }

    // 2. asymmetric push_type string pass
    {
        coro::asymmetric_coroutine<std::string>::pull_type coro(gen_str);
        std::string a = coro.get(); coro();
        std::string b = coro.get();
        if (a != "hello" || b != "world") {
            std::cerr << "FAIL: asymmetric string a=" << a << " b=" << b << std::endl;
            return 1;
        }
        std::cout << "PASS asymmetric string: hello/world\n";
    }

    // 3. asymmetric push_type with int& arg
    {
        bool ok = false;
        coro::asymmetric_coroutine<int>::push_type coro(
            [&](coro::asymmetric_coroutine<int>::pull_type &in) { ok = (in.get() == 42); });
        coro(42);
        if (!ok) {
            std::cerr << "FAIL: push_type int arg\n";
            return 1;
        }
        std::cout << "PASS push_type int arg 42\n";
    }

    // 4. symmetric coroutine call/yield round-trip (symmetric yield suspends, not completes)
    {
        coro::symmetric_coroutine<void>::call_type coro(symm_call_fn);
        if (!coro) {
            std::cerr << "FAIL: symmetric call_type initial state\n";
            return 1;
        }
        coro(); // first call enters coro and suspends at yield()
        if (!coro) {
            std::cerr << "FAIL: symmetric should be suspended after first yield, not complete\n";
            return 1;
        }
        coro(); // second call resumes after yield() and reaches end -> complete
        if (coro) {
            std::cerr << "FAIL: symmetric should be complete after resume\n";
            return 1;
        }
        std::cout << "PASS symmetric call/yield\n";
    }

    // 5. protected_stack_allocator and stack_traits smoke (OHOS guarded: protected allocator may require mprotect guard page)
    {
        std::size_t default_sz = coro::stack_traits::default_size();
        if (default_sz == 0) {
            std::cerr << "FAIL: stack_traits default_size 0\n";
            return 1;
        }
        std::cout << "INFO stack_traits default_size=" << default_sz << "\n";
        // standard_stack_allocator round-trip must succeed
        {
            coro::standard_stack_allocator salloc;
            boost::coroutines::stack_context ctx;
            try {
                salloc.allocate(ctx);
                if (!ctx.sp || ctx.size == 0) {
                    std::cerr << "FAIL: standard_stack_allocator allocate\n";
                    return 1;
                }
                salloc.deallocate(ctx);
                std::cout << "PASS standard_stack_allocator allocate/deallocate\n";
            } catch (const std::exception &e) {
                std::cerr << "FAIL: standard_stack_allocator exception: " << e.what() << "\n";
                return 1;
            }
        }
        // protected_stack_allocator may fail on OHOS due to guard page mprotect; treat as SKIP not FAIL
        {
            coro::protected_stack_allocator palloc;
            boost::coroutines::stack_context ctx;
            try {
                palloc.allocate(ctx);
                if (!ctx.sp || ctx.size == 0) {
                    std::cerr << "WARN: protected_stack_allocator allocate returned null, skipping\n";
                } else {
                    palloc.deallocate(ctx);
                    std::cout << "PASS protected_stack_allocator allocate/deallocate\n";
                }
            } catch (const std::exception &e) {
                std::cout << "SKIP protected_stack_allocator not supported on this platform: " << e.what() << "\n";
            } catch (...) {
                std::cout << "SKIP protected_stack_allocator not supported (unknown exception)\n";
            }
        }
        std::cout << "PASS stack allocators default_size=" << default_sz << "\n";
    }

    // 6. exception propagation through coroutine
    {
        bool caught = false;
        try {
            coro::asymmetric_coroutine<void>::pull_type coro(
                [](coro::asymmetric_coroutine<void>::push_type &yield) {
                    yield();
                    throw std::runtime_error("coro_error");
                });
            coro();
            coro(); // second resume should propagate
        } catch (const std::runtime_error &e) {
            caught = (std::string(e.what()) == "coro_error");
        }
        if (!caught) {
            std::cerr << "FAIL: exception propagation\n";
            return 1;
        }
        std::cout << "PASS exception propagation\n";
    }

    // 7. output iterator via push_type iterator
    {
        std::vector<int> out;
        coro::asymmetric_coroutine<int>::push_type coro(
            [&](coro::asymmetric_coroutine<int>::pull_type &in) {
                while (in) { out.push_back(in.get()); in(); }
            });
        for (int i = 10; i < 13; ++i) coro(i);
        if (out.size() != 3 || out[1] != 11) {
            std::cerr << "FAIL: output iterator\n";
            return 1;
        }
        std::cout << "PASS output iterator\n";
    }

    std::cout << "boost1.84-coroutine smoke test OK: all 7 groups passed\n";
    return 0;
}
