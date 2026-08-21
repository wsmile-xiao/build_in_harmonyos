// test_package for atomic_queue 1.9.2 — ports ALL 9 upstream tests (no Boost).
//
// Ported from src/tests.cc (Boost.Test) to standalone C++ with check() helper.
// All 9 BOOST_AUTO_TEST_CASEs covered:
//   1. stress              → test_stress_mpmc + test_stress_spsc
//   2. move_only_element   → test_move_only_element
//   3. allocator_constructor_only_b  → test_allocator_constructor_b
//   4. allocator_constructor_only_b2 → test_allocator_constructor_b2
//   5. move_constructor_assignment   → test_move_constructor_assignment
//   6. try_push_pop        → test_try_push_pop
//   7. size                → test_size
//   8. power_of_2          → test_power_of_2 (static_assert)
//   9. remap_index         → test_remap_index

#include "atomic_queue/atomic_queue.h"
#include "atomic_queue/barrier.h"

#include <atomic>
#include <bitset>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>

namespace {

int g_failures = 0;

void check(bool cond, const char* name)
{
    if (cond) {
        std::printf("PASS: %s\n", name);
    } else {
        std::printf("FAIL: %s\n", name);
        ++g_failures;
    }
    std::fflush(stdout);
}

// --- Helpers from benchmarks.h (inlined to avoid dependency) ---

template<class Queue, size_t Capacity>
struct CapacityArgAdaptor : Queue {
    ATOMIC_QUEUE_INLINE CapacityArgAdaptor()
        : Queue(Capacity)
    {}
};

template<class Queue>
struct RetryDecorator : Queue {
    using T = typename Queue::value_type;
    using Queue::Queue;

    ATOMIC_QUEUE_INLINE void push(T element) noexcept {
        while (ATOMIC_QUEUE_UNLIKELY(!this->try_push(element)))
            atomic_queue::spin_loop_pause();
    }

    ATOMIC_QUEUE_INLINE T pop() noexcept {
        T element;
        while (ATOMIC_QUEUE_UNLIKELY(!this->try_pop(element)))
            atomic_queue::spin_loop_pause();
        return element;
    }
};

// --- Stateful allocator from tests.cc ---

template<class T, class State>
struct test_stateful_allocator : std::allocator<T> {
    State state;
    test_stateful_allocator() = delete;

    test_stateful_allocator(std::nullptr_t, const State& s) noexcept
        : state(s) {}

    test_stateful_allocator(const test_stateful_allocator& other) noexcept
        : std::allocator<T>(other), state(other.state) {}

    template<class U>
    test_stateful_allocator(const test_stateful_allocator<U, State>& other) noexcept
        : state(other.state) {}

    test_stateful_allocator& operator=(const test_stateful_allocator& other) noexcept {
        state = other.state;
        return *this;
    }

    ~test_stateful_allocator() noexcept = default;

    template<class U>
    struct rebind {
        using other = test_stateful_allocator<U, State>;
    };
};

template<class T1, class T2, class State>
bool operator==(const test_stateful_allocator<T1, State>& lhs,
                const test_stateful_allocator<T2, State>& rhs) {
    return lhs.state == rhs.state;
}

template<class T1, class T2, class State>
bool operator!=(const test_stateful_allocator<T1, State>& lhs,
                const test_stateful_allocator<T2, State>& rhs) {
    return !(lhs.state == rhs.state);
}

} // namespace

// ===========================================================================
// Test 1: stress_mpmc — port of upstream "stress" (MPMC variant)
//
// 3 producers × 100k elements, 3 consumers. Barrier2 for synchronized start.
// Consumers pop until STOP sentinel. Verify total sum.
// ===========================================================================
static void test_stress_mpmc()
{
    constexpr unsigned CAPACITY = 4096;
    constexpr unsigned N_STRESS = 100000;
    constexpr unsigned NIL = ~0u;
    constexpr unsigned STOP = 0u;
    constexpr int PRODUCERS = 3;
    constexpr int CONSUMERS = 3;
    using Queue = atomic_queue::AtomicQueueB<unsigned, std::allocator<unsigned>, NIL>;

    Queue q{CAPACITY};
    atomic_queue::Barrier2 barrier = {{PRODUCERS + CONSUMERS}};

    uint64_t results[CONSUMERS] = {};

    std::thread consumers[CONSUMERS];
    for (int i = 0; i < CONSUMERS; ++i)
        consumers[i] = std::thread([&, i]() {
            barrier.countdown();
            uint64_t sum = 0;
            unsigned n;
            while ((n = q.pop()) != STOP)
                sum += n;
            results[i] = sum;
        });

    std::thread producers[PRODUCERS];
    for (auto& p : producers)
        p = std::thread([&]() {
            barrier.countdown();
            for (unsigned n = N_STRESS; n > 0; --n)
                q.push(n);
        });

    for (auto& p : producers) p.join();
    for (int i = 0; i < CONSUMERS; ++i) q.push(STOP);
    for (auto& c : consumers) c.join();

    constexpr uint64_t expected = uint64_t(N_STRESS + 1) * N_STRESS / 2 * PRODUCERS;
    uint64_t total = 0;
    for (auto r : results) total += r;
    check(total == expected, "stress_mpmc: 3P/3C sum integrity (300k elements)");
}

// ===========================================================================
// Test 2: stress_spsc — port of upstream "stress" (SPSC variant)
// ===========================================================================
static void test_stress_spsc()
{
    constexpr unsigned CAPACITY = 4096;
    constexpr unsigned N_STRESS = 100000;
    constexpr unsigned NIL = ~0u;
    using Queue = atomic_queue::AtomicQueueB<unsigned, std::allocator<unsigned>, NIL>;

    Queue q{CAPACITY};
    uint64_t consumer_sum = 0;

    std::thread consumer([&]() {
        uint64_t sum = 0;
        for (unsigned i = 0; i < N_STRESS; ++i) {
            unsigned val;
            while ((val = q.pop()) == NIL)
                ;
            sum += val;
        }
        consumer_sum = sum;
    });

    std::thread producer([&]() {
        for (unsigned n = N_STRESS; n > 0; --n)
            q.push(n);
    });

    producer.join();
    consumer.join();

    constexpr uint64_t expected = uint64_t(N_STRESS + 1) * N_STRESS / 2;
    check(consumer_sum == expected, "stress_spsc: 1P/1C sum integrity (100k elements)");
}

// ===========================================================================
// Test 3: move_only_element — port of upstream "move_only_element"
//
// Tests AtomicQueueB2 with std::unique_ptr<int>. Verifies try_push, push,
// try_pop, pop, was_empty, was_size with move-only types.
// ===========================================================================
static void test_move_only_element()
{
    constexpr unsigned CAPACITY = 64;
    using Queue = atomic_queue::AtomicQueueB2<std::unique_ptr<int>>;

    Queue q{CAPACITY};
    check(q.was_empty(), "move_only: initially empty");
    check(q.was_size() == 0u, "move_only: initially size==0");

    // try_push a unique_ptr.
    std::unique_ptr<int> p{new int{1}};
    check(q.try_push(std::move(p)), "move_only: try_push(unique_ptr) succeeds");
    check(!p, "move_only: source moved-from after try_push");
    check(!q.was_empty(), "move_only: not empty after try_push");
    check(q.was_size() == 1u, "move_only: size==1 after try_push");

    // push another unique_ptr.
    p.reset(new int{2});
    q.push(std::move(p));
    check(!p, "move_only: source moved-from after push");
    check(q.was_size() == 2u, "move_only: size==2 after push");

    // try_pop in FIFO order.
    check(q.try_pop(p), "move_only: try_pop succeeds");
    check(p && *p == 1, "move_only: try_pop returns value 1 (FIFO)");
    check(!q.was_empty(), "move_only: not empty after try_pop");
    check(q.was_size() == 1u, "move_only: size==1 after try_pop");

    // pop second element.
    p = q.pop();
    check(p && *p == 2, "move_only: pop returns value 2 (FIFO)");
    check(q.was_empty(), "move_only: empty after popping all");
    check(q.was_size() == 0u, "move_only: size==0 after popping all");
}

// ===========================================================================
// Test 4: allocator_constructor_only_b — port of upstream test
//
// Tests AtomicQueueB with a stateful allocator. Verifies get_allocator()
// and move constructor preserves allocator.
// ===========================================================================
static void test_allocator_constructor_b()
{
    using allocator_type = test_stateful_allocator<int, std::string>;
    const auto allocator = allocator_type(nullptr, "Capybara");

    atomic_queue::AtomicQueueB<int, allocator_type> q(2, allocator);

    check(q.get_allocator() == allocator, "alloc_b: get_allocator matches");
    auto q2 = std::move(q);
    check(q2.get_allocator() == allocator, "alloc_b: move preserves allocator");
}

// ===========================================================================
// Test 5: allocator_constructor_only_b2 — port of upstream test
//
// Tests AtomicQueueB2 with a stateful allocator (move-only element type).
// ===========================================================================
static void test_allocator_constructor_b2()
{
    using allocator_type = test_stateful_allocator<std::unique_ptr<int>, std::string>;
    const auto allocator = allocator_type(nullptr, "Fox");

    atomic_queue::AtomicQueueB2<std::unique_ptr<int>, allocator_type> q(2, allocator);

    check(q.get_allocator() == allocator, "alloc_b2: get_allocator matches");
    auto q2 = std::move(q);
    check(q2.get_allocator() == allocator, "alloc_b2: move preserves allocator");
}

// ===========================================================================
// Test 6: move_constructor_assignment — port of upstream test
//
// Verifies move constructor and move assignment transfer capacity correctly.
// Uses CapacityArgAdaptor (inlined helper).
// ===========================================================================
static void test_move_constructor_assignment()
{
    // Test AtomicQueueB<int> with capacity 2
    {
        using Queue = CapacityArgAdaptor<atomic_queue::AtomicQueueB<int>, 2>;
        Queue q;
        auto const capacity = q.capacity();
        check(capacity >= 2, "move_assign_b: capacity >= 2");

        Queue q2 = std::move(q);
        check(!q.capacity(), "move_assign_b: moved-from capacity==0");
        check(q2.capacity() == capacity, "move_assign_b: moved-to has capacity");

        q = std::move(q2);
        check(q.capacity() == capacity, "move_assign_b: assigned-back has capacity");
        check(!q2.capacity(), "move_assign_b: assigned-from capacity==0");
    }

    // Test AtomicQueueB2<unique_ptr<int>> with capacity 2
    {
        using Queue = CapacityArgAdaptor<atomic_queue::AtomicQueueB2<std::unique_ptr<int>>, 2>;
        Queue q;
        auto const capacity = q.capacity();
        check(capacity >= 2, "move_assign_b2: capacity >= 2");

        Queue q2 = std::move(q);
        check(!q.capacity(), "move_assign_b2: moved-from capacity==0");
        check(q2.capacity() == capacity, "move_assign_b2: moved-to has capacity");

        q = std::move(q2);
        check(q.capacity() == capacity, "move_assign_b2: assigned-back has capacity");
        check(!q2.capacity(), "move_assign_b2: assigned-from capacity==0");
    }
}

// ===========================================================================
// Test 7: try_push_pop — port of upstream "try_push_pop"
//
// Exercises try_push, try_pop, was_empty, was_full, was_size, capacity.
// Uses AtomicQueueB2<float, SPSC=true> with capacity = CACHE_LINE_SIZE^2.
// ===========================================================================
static void test_try_push_pop()
{
    using Queue = atomic_queue::AtomicQueueB2<
        float, std::allocator<float>, true, true, true>;

    constexpr unsigned CAP = atomic_queue::CACHE_LINE_SIZE * atomic_queue::CACHE_LINE_SIZE;
    Queue q(CAP);

    check(q.capacity() == CAP, "try_push_pop: capacity == CACHE_LINE_SIZE^2");
    check(q.was_empty(), "try_push_pop: initially empty");
    check(!q.was_full(), "try_push_pop: initially not full");
    check(q.was_size() == 0u, "try_push_pop: initially size==0");

    // try_pop on empty queue must fail.
    float v = -1;
    check(!q.try_pop(v), "try_push_pop: try_pop empty fails");
    check(v == -1, "try_push_pop: try_pop empty doesn't touch v");

    // Fill the queue completely.
    bool all_pushed = true;
    for (unsigned i = 1; i <= CAP; ++i)
        if (!q.try_push(static_cast<float>(i))) { all_pushed = false; break; }
    check(all_pushed, "try_push_pop: try_push CAP elements succeeds");
    check(!q.was_empty(), "try_push_pop: full => not empty");
    check(q.was_full(), "try_push_pop: full => was_full");
    check(q.was_size() == CAP, "try_push_pop: full => size==CAP");

    // try_push on full must fail.
    check(!q.try_push(999.f), "try_push_pop: try_push on full fails");

    // Pop all and verify FIFO order.
    bool order_ok = true;
    for (unsigned i = 1; i <= CAP; ++i) {
        if (!q.try_pop(v) || v != static_cast<float>(i)) { order_ok = false; break; }
    }
    check(order_ok, "try_push_pop: try_pop FIFO order correct");
    check(q.was_empty(), "try_push_pop: empty after popping all");
    check(!q.was_full(), "try_push_pop: not full after popping all");
    check(q.was_size() == 0u, "try_push_pop: size==0 after popping all");

    // try_pop on empty again.
    v = -1;
    check(!q.try_pop(v), "try_push_pop: try_pop empty again fails");
    check(v == -1, "try_push_pop: try_pop empty again doesn't touch v");
}

// ===========================================================================
// Test 8: size — port of upstream "size"
//
// Tests RetryDecorator with AtomicQueueB2<float>. Verifies capacity rounding
// and initial empty/full state.
// ===========================================================================
static void test_size()
{
    RetryDecorator<atomic_queue::AtomicQueueB2<float>> q(10);
    check(q.capacity() == atomic_queue::CACHE_LINE_SIZE * atomic_queue::CACHE_LINE_SIZE,
          "size: capacity rounded to CACHE_LINE_SIZE^2");
    check(q.was_empty(), "size: initially empty");
    check(!q.was_full(), "size: initially not full");
}

// ===========================================================================
// Test 9: power_of_2 — compile-time checks (upstream "power_of_2")
// ===========================================================================
static_assert(atomic_queue::details::round_up_to_power_of_2(0u) == 0u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(1u) == 1u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(2u) == 2u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(3u) == 4u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(127u) == 128u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(128u) == 128u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(129u) == 256u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(0x40000000u - 1) == 0x40000000u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(0x40000000u    ) == 0x40000000u, "");
static_assert(atomic_queue::details::round_up_to_power_of_2(0x40000000u + 1) == 0x80000000u, "");

static void test_power_of_2()
{
    check(true, "power_of_2: 10 static_assert checks passed at compile time");
}

// ===========================================================================
// Test 10: remap_index — port of upstream "remap_index"
//
// Verifies RemapXor and RemapAnd: BITS=0 identity, bit-swap correctness,
// self-inverse property, bijection over power-of-2 range.
// ===========================================================================
static void test_remap_index()
{
    using namespace atomic_queue::details;

    constexpr auto bits0 = IndexBits<0>{};
    constexpr auto bits1 = IndexBits<1>{};
    constexpr auto bits2 = IndexBits<2>{};
    constexpr auto bits3 = IndexBits<3>{};
    constexpr auto bits4 = IndexBits<4>{};

    auto test_one = [&](auto remap_fn, const char* name) {
        Remap0<decltype(remap_fn)> remap;

        // BITS=0 is identity.
        bool identity_ok = true;
        for (unsigned i = 256; i--;)
            if (remap(bits0, i) != i) { identity_ok = false; break; }
        check(identity_ok, (std::string(name) + ": BITS=0 identity").c_str());

        // BITS=1 swap.
        bool b1 = remap(bits1, 0b00u) == 0b00u
               && remap(bits1, 0b01u) == 0b10u
               && remap(bits1, 0b10u) == 0b01u
               && remap(bits1, 0b11u) == 0b11u
               && remap(bits1, 0b100u) == 0b100u
               && remap(bits1, 0b101u) == 0b110u;
        check(b1, (std::string(name) + ": BITS=1 swap").c_str());

        // BITS=2 swap.
        bool b2 = remap(bits2, 0b0001u) == 0b0100u
               && remap(bits2, 0b0100u) == 0b0001u
               && remap(bits2, 0b0110u) == 0b1001u
               && remap(bits2, 0b1111u) == 0b1111u;
        check(b2, (std::string(name) + ": BITS=2 swap").c_str());

        // BITS=3 swap.
        bool b3 = remap(bits3, 0b000'001u) == 0b001'000u
               && remap(bits3, 0b001'000u) == 0b000'001u;
        check(b3, (std::string(name) + ": BITS=3 swap").c_str());

        // Self-inverse: remap(remap(i)) == i over 1024 elements.
        constexpr unsigned SIZE = 1024;
        bool inv = true;
        for (unsigned i = SIZE; i--;) {
            if (remap(bits1, remap(bits1, i, SIZE), SIZE) != i) { inv = false; break; }
            if (remap(bits2, remap(bits2, i, SIZE), SIZE) != i) { inv = false; break; }
            if (remap(bits3, remap(bits3, i, SIZE), SIZE) != i) { inv = false; break; }
            if (remap(bits4, remap(bits4, i, SIZE), SIZE) != i) { inv = false; break; }
        }
        check(inv, (std::string(name) + ": self-inverse over 1024").c_str());

        // Bijection over 8-bit range (BITS=3).
        constexpr unsigned N = 256;
        std::bitset<N> seen;
        for (unsigned i = N; i--;) {
            auto j = remap(bits3, i);
            if (j >= N) { inv = false; break; }
            seen.set(j);
        }
        check(seen.count() == N, (std::string(name) + ": bijection over [0,256)").c_str());
    };

    test_one(RemapXor{}, "RemapXor");
    test_one(RemapAnd{}, "RemapAnd");
}

// ===========================================================================
int main()
{
    std::printf("=== atomic_queue 1.9.2 test_package (9/9 upstream tests) ===\n");
    std::fflush(stdout);

    test_stress_mpmc();                 // upstream #1 (MPMC)
    test_stress_spsc();                 // upstream #1 (SPSC)
    test_move_only_element();           // upstream #2
    test_allocator_constructor_b();     // upstream #3
    test_allocator_constructor_b2();    // upstream #4
    test_move_constructor_assignment(); // upstream #5
    test_try_push_pop();                // upstream #6
    test_size();                        // upstream #7
    test_power_of_2();                  // upstream #8
    test_remap_index();                 // upstream #9

    std::printf("\n%s (%d/%d tests passed)\n",
                g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED",
                10 - g_failures, 10);
    return g_failures == 0 ? 0 : 1;
}
