// test_package/test_consumer.cpp - libtut 0.0.20070706 consumer use case
//
// Scenario: a real consumer module (fixed-capacity ring buffer with
// sliding-window statistics) is driven by TUT as its unit test framework
// - the intended usage of this library (testing YOUR code with TUT,
// as opposed to test_libtut which verifies TUT's own semantics).
//
// Two test groups cover the module; the suite is expected all-green:
// exit code 0. Complements test_libtut (which contains one deliberate
// failure and asserts the framework reports it).
//
// ASCII-only comments on purpose: MSVC reads sources as CP936 by default.

#include <tut/tut.hpp>
#include <tut/tut_reporter.hpp>

#include <cstddef>
#include <cstdio>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace tut
{
test_runner_singleton runner;
}

// ---------------------------------------------------------------------
// module under test: fixed-capacity ring buffer with sliding mean
// (typical sensor/telemetry consumer component)
// ---------------------------------------------------------------------
class ring_buffer
{
public:
    explicit ring_buffer(std::size_t capacity)
        : buf_(capacity), cap_(capacity), head_(0), count_(0)
    {
        if (capacity == 0)
        {
            throw std::invalid_argument("capacity must be positive");
        }
    }

    void push(double v)
    {
        buf_[head_] = v;
        head_ = (head_ + 1) % cap_;
        if (count_ < cap_)
        {
            ++count_;
        }
    }

    std::size_t size() const { return count_; }
    std::size_t capacity() const { return cap_; }
    bool empty() const { return count_ == 0; }

    // oldest-first element access
    double at(std::size_t i) const
    {
        if (i >= count_)
        {
            throw std::out_of_range("ring_buffer::at");
        }
        return buf_[(head_ + cap_ - count_ + i) % cap_];
    }

    double mean() const
    {
        if (count_ == 0)
        {
            throw std::out_of_range("ring_buffer::mean on empty buffer");
        }
        double sum = 0.0;
        for (std::size_t i = 0; i < count_; ++i)
        {
            sum += at(i);
        }
        return sum / static_cast<double>(count_);
    }

private:
    std::vector<double> buf_;
    std::size_t cap_;
    std::size_t head_;
    std::size_t count_;
};

// ---------------------------------------------------------------------
// module under test: token accumulator (join/clear semantics)
// ---------------------------------------------------------------------
class token_accumulator
{
public:
    void append(const std::string& tok) { toks_.push_back(tok); }

    std::string join(const std::string& sep) const
    {
        std::string out;
        for (std::size_t i = 0; i < toks_.size(); ++i)
        {
            if (i > 0)
            {
                out += sep;
            }
            out += toks_[i];
        }
        return out;
    }

    void clear() { toks_.clear(); }
    std::size_t size() const { return toks_.size(); }

private:
    std::vector<std::string> toks_;
};

// ---------------------------------------------------------------------
// TUT test groups (the consumer's own tests, written with libtut)
// ---------------------------------------------------------------------
namespace tut
{

struct rb_data
{
};

typedef test_group<rb_data> rb_tf;
typedef rb_tf::object rb_object;
namespace { rb_tf rb_group("consumer ring buffer"); }

template<> template<>
void rb_object::test<1>()
{
    set_test_name("FIFO overwrite: oldest evicted at capacity");
    ring_buffer rb(3);
    rb.push(1);
    rb.push(2);
    rb.push(3);
    ensure_equals("full", rb.size(), static_cast<std::size_t>(3));
    rb.push(4);  // evicts 1
    ensure_equals("size capped at capacity",
                  rb.size(), static_cast<std::size_t>(3));
    ensure_equals("oldest is now 2", rb.at(0), 2.0);
    ensure_equals("newest is 4", rb.at(2), 4.0);
}

template<> template<>
void rb_object::test<2>()
{
    set_test_name("sliding mean over the window");
    ring_buffer rb(4);
    for (double v = 1.0; v <= 4.0; v += 1.0)
    {
        rb.push(v);
    }
    ensure_distance("mean of 1..4 is 2.5 (strictly inside bounds)",
                    rb.mean(), 2.5, 0.5);
    rb.push(10.0);  // window becomes 2,3,4,10
    ensure_equals("mean after slide", rb.mean(), 4.75);
}

template<> template<>
void rb_object::test<3>()
{
    set_test_name("empty-buffer access contract throws out_of_range");
    ring_buffer rb(2);
    ensure("starts empty", rb.empty());
    bool threw = false;
    try
    {
        rb.at(0);
    }
    catch (const std::out_of_range&)
    {
        threw = true;
    }
    ensure("at() on empty throws", threw);
    threw = false;
    try
    {
        rb.mean();
    }
    catch (const std::out_of_range&)
    {
        threw = true;
    }
    ensure("mean() on empty throws", threw);
}

template<> template<>
void rb_object::test<4>()
{
    set_test_name("zero capacity rejected at construction");
    bool threw = false;
    try
    {
        ring_buffer rb(0);
    }
    catch (const std::invalid_argument&)
    {
        threw = true;
    }
    ensure("zero-capacity ctor throws invalid_argument", threw);
}

struct acc_data
{
};

typedef test_group<acc_data> acc_tf;
typedef acc_tf::object acc_object;
namespace { acc_tf acc_group("consumer token accumulator"); }

template<> template<>
void acc_object::test<1>()
{
    set_test_name("append + join with separator");
    token_accumulator acc;
    acc.append("ohos");
    acc.append("libtut");
    acc.append("consumer");
    ensure_equals("token count", acc.size(), static_cast<std::size_t>(3));
    ensure_equals("joined", acc.join("-"), std::string("ohos-libtut-consumer"));
}

template<> template<>
void acc_object::test<2>()
{
    set_test_name("clear resets the accumulator");
    token_accumulator acc;
    acc.append("a");
    acc.append("b");
    acc.clear();
    ensure_equals("empty after clear", acc.size(), static_cast<std::size_t>(0));
    ensure_equals("join of empty is empty string", acc.join(","), std::string(""));
}

} // namespace tut

// ---------------------------------------------------------------------
// test driver: official reporter pass + exact counting pass
// ---------------------------------------------------------------------
namespace
{

struct counters
{
    int total;
    int ok;
    int fail;
    int ex;
    counters() : total(0), ok(0), fail(0), ex(0) {}
};

class counting_callback : public tut::callback
{
public:
    void run_started() { per_group.clear(); }

    void test_completed(const tut::test_result& tr)
    {
        counters& c = per_group[tr.group];
        ++c.total;
        switch (tr.result)
        {
        case tut::test_result::ok:   ++c.ok;   break;
        case tut::test_result::fail: ++c.fail; break;
        case tut::test_result::ex:   ++c.ex;   break;
        default: break;
        }
    }

    std::map<std::string, counters> per_group;
};

int g_failures = 0;

void check(bool cond, const char* what)
{
    if (cond)
    {
        std::printf("PASS: %s\n", what);
    }
    else
    {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

} // namespace

int main()
{
    // pass 1: official tut::reporter - a consumer suite must be all green
    {
        tut::reporter reporter;
        tut::runner.get().set_callback(&reporter);
        tut::runner.get().run_tests();
        check(reporter.all_ok() == true,
              "tut::reporter: consumer suite is all green");
    }

    // pass 2: exact result-type accounting
    counting_callback cnt;
    tut::runner.get().set_callback(&cnt);
    tut::runner.get().run_tests();

    const std::map<std::string, counters>& g = cnt.per_group;
    check(g.size() == 2, "2 consumer test groups registered");

    std::map<std::string, counters>::const_iterator rb =
        g.find("consumer ring buffer");
    std::map<std::string, counters>::const_iterator acc =
        g.find("consumer token accumulator");

    check(rb != g.end(), "ring buffer group ran");
    if (rb != g.end())
    {
        check(rb->second.total == 4, "ring buffer: 4 tests run");
        check(rb->second.ok == 4 && rb->second.fail == 0 && rb->second.ex == 0,
              "ring buffer: 4 ok / 0 fail / 0 ex");
    }

    check(acc != g.end(), "token accumulator group ran");
    if (acc != g.end())
    {
        check(acc->second.total == 2, "accumulator: 2 tests run");
        check(acc->second.ok == 2 && acc->second.fail == 0 && acc->second.ex == 0,
              "accumulator: 2 ok / 0 fail / 0 ex");
    }

    if (g_failures == 0)
    {
        std::printf("test_consumer: ALL CHECKS PASSED\n");
    }
    return g_failures == 0 ? 0 : 1;
}
