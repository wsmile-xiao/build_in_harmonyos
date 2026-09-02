#include <c4/std/string.hpp>
#include <iostream>
#include <c4/substr.hpp>
#include <c4/log/log.hpp>
#include <string>
#include <vector>
#include <stdexcept>

#define CHECK_EQ(a,b) do { auto _a=(a); auto _b=(b); if (!(_a==_b)) { std::cerr << "CHECK_EQ failed at " << __FILE__ << ":" << __LINE__ << " : " #a " != " #b << std::endl; throw std::runtime_error("CHECK_EQ"); } } while(0)
#define CHECK_GT(a,b) do { if (!((a)>(b))) { std::cerr << "CHECK_GT failed at " << __FILE__ << ":" << __LINE__ << std::endl; throw std::runtime_error("CHECK_GT"); } } while(0)

std::string logrcv;
void test_logpump(const char* c_str, size_t len)
{
    logrcv.append(c_str, len);
}

struct SetupLogTest
{
    SetupLogTest()
    {
        logrcv.clear();
        logrcv.shrink_to_fit();
        c4::logns::set_logpump(&test_logpump);
    }
    ~SetupLogTest()
    {
        c4::logns::set_logpump(nullptr);
    }
};

void shrink_buf()
{
    auto * buf = c4::logns::detail::_dump_buf();
    buf->len = 8;
    buf->shrink_to_fit();
}

struct LargeType1
{
    std::vector<std::string> s;
};

struct LargeType2
{
    std::vector<std::string> s;
};

size_t to_chars(c4::substr buf, LargeType1 const& v)
{
    size_t total = 0;
    for(std::string const& s : v.s)
    {
        c4::substr curr = total < buf.len ? buf.sub(total) : c4::substr();
        total += to_chars(curr, s);
    }
    return total;
}

C4_ALWAYS_INLINE void dump_(LargeType2 const& C4_RESTRICT v, c4::logns::pfn_logpump fn, c4::logns::detail::DumpBuf *buf)
{
    for(std::string const& s : v.s)
    {
        c4::catrs(buf, s);
        fn(buf->data(), buf->size());
    }
}

template<class T>
struct LargeTypeWithSizes
{
    T var;
    size_t szmax;
    size_t sztotal;
};

template<class T>
LargeTypeWithSizes<T> make_(size_t num)
{
    LargeTypeWithSizes<T> lt;
    lt.szmax = 0;
    lt.sztotal = 0;
    auto &strvec = lt.var.s;
    strvec.resize(num);
    for(size_t i = 0; i < num; ++i)
    {
        strvec[i].resize((size_t(1u) << (i + 1)) - 1, static_cast<char>('0' + i));
        strvec[i] += '\n';
        lt.szmax = std::max(strvec[i].size(), lt.szmax);
        lt.sztotal += strvec[i].size();
    }
    return lt;
}

void test_dump_overloading_dump_uses_less_space()
{
    auto setup = SetupLogTest();
    shrink_buf();
    auto const* buf = c4::logns::detail::_dump_buf();
    size_t szbefore = buf->capacity();
    auto var_and_size = make_<LargeType2>(10);
    c4::logns::print(var_and_size.var);
    size_t szafter = buf->capacity();
    CHECK_GT(szafter, szbefore);
    CHECK_EQ(szafter, var_and_size.szmax);
}

void test_dump_overloading_to_chars_uses_more_space()
{
    auto setup = SetupLogTest();
    shrink_buf();
    auto const* buf = c4::logns::detail::_dump_buf();
    size_t szbefore = buf->capacity();
    auto var_and_size = make_<LargeType1>(10);
    c4::logns::print(var_and_size.var);
    size_t szafter = buf->capacity();
    CHECK_GT(szafter, szbefore);
    CHECK_EQ(szafter, var_and_size.sztotal);
}

template <class... Args>
void test_print(c4::csubstr expected, Args && ...args)
{
    {
        auto h = SetupLogTest();
        c4::logns::print(std::forward<Args>(args)...);
    }
    CHECK_EQ(c4::to_csubstr(logrcv), expected);
}

template <class T, class... Args>
void test_printsep(c4::csubstr expected, c4::logns::Sep<T> s, Args && ...args)
{
    {
        auto h = SetupLogTest();
        c4::logns::printsep(s, std::forward<Args>(args)...);
    }
    CHECK_EQ(c4::to_csubstr(logrcv), expected);
}

template <class... Args>
void test_log(c4::csubstr expected, c4::csubstr fmt, Args && ...args)
{
    {
        auto h = SetupLogTest();
        c4::logns::log(fmt, std::forward<Args>(args)...);
    }
    CHECK_EQ(c4::to_csubstr(logrcv), expected);
}

void test_log_print()
{
    test_print("FDX\n", "FDX");
    test_print("FDX 1 2 3\n", "FDX", 1, 2, 3);
}

void test_log_printsep()
{
    using namespace c4::logns;
    test_printsep("FDX\n", sep('-'), "FDX");
    test_printsep("FDX\n", sep(std::string("wtf")), "FDX");
    test_printsep("FDX-1-2-3\n", sep('-'), "FDX", 1, 2, 3);
    test_printsep("FDX---wtf---1---wtf---2---wtf---3\n", sep(std::string("---wtf---")), "FDX", 1, 2, 3);
}

void test_log_log()
{
    test_log("the cat ate the mouse\n", "the {} ate the {}", "cat", "mouse");
}

int main()
{
    int total = 5;
    int passed = 0;
    int failed = 0;
    struct Case { const char* name; void (*fn)(); };
    Case cases[] = {
        {"dump.overloading_dump_uses_less_space", test_dump_overloading_dump_uses_less_space},
        {"dump.overloading_to_chars_uses_more_space", test_dump_overloading_to_chars_uses_more_space},
        {"log.print", test_log_print},
        {"log.printsep", test_log_printsep},
        {"log.log", test_log_log},
    };
    for (auto &c : cases) {
        try {
            c.fn();
            std::cout << "[PASS] " << c.name << std::endl;
            ++passed;
        } catch (std::exception const& e) {
            std::cout << "[FAIL] " << c.name << " : " << e.what() << std::endl;
            ++failed;
        } catch (...) {
            std::cout << "[FAIL] " << c.name << " : unknown" << std::endl;
            ++failed;
        }
    }
    std::cout << "doctest cases: " << total << " | " << passed << " passed | " << failed << " failed" << std::endl;
    return failed == 0 ? 0 : 1;
}
