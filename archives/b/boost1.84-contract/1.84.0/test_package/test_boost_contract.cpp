// test_boost_contract.cpp — boost1.84-contract 1.84.0 L1 冒烟测试
//
// 实质验证 Boost.Contract 核心能力面（R34：调用被测包真实 API）：
//   1. 自由函数契约（precondition/postcondition）
//   2. 成员函数契约 + 类不变式（public_function）
//   3. call_if 编译期条件分派（需 <boost/type_traits/has_equal_to.hpp>）
//   4. 断言失败可观察性（set_postcondition_failure 抛异常，官方
//      "Throw on Failure" 模式，单进程内完成验证）
//
// 运行环境：HarmonyOS PC (aarch64, clang 15, libc++)，C++17。

#include <boost/contract.hpp>
#include <boost/bind.hpp>
#include <boost/type_traits/has_equal_to.hpp>

#include <cassert>
#include <cstdio>
#include <functional>
#include <stdexcept>
#include <string>

// ── 1. 自由函数契约：前置/后置条件 ────────────────────────────────
int inc(int& x) {
    int result;
    boost::contract::check c = boost::contract::function()
        .precondition([&] { BOOST_CONTRACT_ASSERT(x < 100); })
        .postcondition([&] { BOOST_CONTRACT_ASSERT(x == result); })
    ;
    return result = ++x;
}

// ── 2. 类不变式 + 成员函数契约（public_function）────────────────
class counter {
public:
    counter() : n_(0) {}

    void increment() {
        boost::contract::check c = boost::contract::public_function(this)
            .precondition([&] { BOOST_CONTRACT_ASSERT(n_ < 1000); })
            .postcondition([&] { BOOST_CONTRACT_ASSERT(n_ == n_before + 1); })
        ;
        n_before = n_;
        ++n_;
    }

    int n() const {
        boost::contract::check c = boost::contract::public_function(this);
        return n_;
    }

private:
    int n_;
    int n_before = 0;
};

// ── 3. call_if：编译期条件分派（contract 组件特性）────────────────
struct no_eq {};  // 无 operator==

// 上游测试（libs/contract/test/call_if/）同款技巧：用 bind 延迟求值，
// no_eq 分支的 operator() 只有被真正调用时才实例化（call_if false 分支
// 不会调用它，故对无 operator== 的类型也能编译）。
template<typename T>
bool safe_equal(T const& l, T const& r) {
    return boost::contract::call_if_c<boost::has_equal_to<T>::value>(
        boost::bind(std::equal_to<T>(), l, r)
    ).else_(
        [] { return false; }
    );
}

// ── 4. 断言失败可观察性：Throw on Failure 模式 ──────────────────
// 后置条件必然违反的函数（用于验证 failure 路径可被捕获）
int bad_inc(int& x) {
    int result;
    boost::contract::check c = boost::contract::function()
        .postcondition([&] { BOOST_CONTRACT_ASSERT(result == x + 100); })  // 永假
    ;
    return result = ++x;
}

int main() {
    // 官方 Throw on Failure 模式：violation 时抛异常而非 terminate
    boost::contract::set_postcondition_failure(
        [](boost::contract::from) { throw std::logic_error("postcondition violated"); });

    // 1. 自由函数契约
    int x = 10;
    assert(inc(x) == 11);
    assert(x == 11);

    // 2. 类不变式 + 成员函数契约
    counter c;
    assert(c.n() == 0);
    c.increment();
    c.increment();
    assert(c.n() == 2);

    // 3. call_if 编译期分派
    assert(safe_equal(1, 1) == true);
    assert(safe_equal(std::string("a"), std::string("a")) == true);
    assert(safe_equal(no_eq(), no_eq()) == false);

    // 4. violation 路径：后置条件违反必须抛出并可捕获
    int y = 5;
    bool caught = false;
    try {
        bad_inc(y);
    } catch (std::logic_error const& e) {
        caught = true;
    }
    assert(caught);   // 契约违反被捕获
    assert(y == 6);   // 函数本身语义不受影响

    printf("boost1.84-contract test_package PASSED "
           "(pre/post/invariant/call_if/violation)\n");
    return 0;
}
