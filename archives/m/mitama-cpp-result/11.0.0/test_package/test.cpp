// test_package/test.cpp — mitama-cpp-result 11.0.0 consumer test (HarmonyOS PC).
//
// 验证 Conan 打包后的 mitama::result<T, E> 头文件库，不直接 include 上游源码树。
// 覆盖：
//   ① success result 取值 (is_ok / unwrap / unwrap_or)
//   ② error result 取值 (is_err / unwrap_err / unwrap_or)
//   ③ map — 成功分支变换
//   ④ map_err — 错误分支变换
//   ⑤ and_then — 成功分支链式组合（返回新 result）
//   ⑥ or_else — 错误分支链式组合（返回新 result）
//   ⑦ map 在错误分支上保持错误不变
//   ⑧ and_then 在错误分支上保持错误不变
//   ⑨ or_else 在成功分支上保持成功不变
//   ⑩ 成功/错误分支互斥
//
// 每个 CHECK 打印一行；末尾打印 PASS/FAIL 汇总。非仅 include 编译测试。
#include <mitama/result/result.hpp>

#include <functional>
#include <iostream>
#include <sstream>
#include <string>

/* CHECK 宏：断言失败则打印 got/want 并立即返回 1。 */
#define CHECK(label, got, want)                                        \
    do {                                                               \
        g_checks_total++;                                              \
        std::ostringstream _g, _w;                                     \
        _g << (got);                                                   \
        _w << (want);                                                  \
        if (_g.str() == _w.str()) {                                    \
            std::cout << "CHECK " << label << " : PASS" << std::endl;  \
        } else {                                                       \
            std::cout << "CHECK " << label << " : FAIL" << std::endl;  \
            std::cout << "  got:  " << _g.str() << std::endl;          \
            std::cout << "  want: " << _w.str() << std::endl;          \
            return 1;                                                  \
        }                                                              \
    } while (0)

static int g_checks_total = 0;

int main() {
    using namespace mitama;

    // ── ① success result 取值 ────────────────────────────────────────
    result<int, int> ok_res = success_t<int>{42};
    CHECK("ok.is_ok", ok_res.is_ok(), true);
    CHECK("ok.is_err", ok_res.is_err(), false);
    CHECK("ok.unwrap", ok_res.unwrap(), 42);
    CHECK("ok.unwrap_or", ok_res.unwrap_or(0), 42);

    // ── ② error result 取值 ──────────────────────────────────────────
    result<int, int> err_res = failure_t<int>{7};
    CHECK("err.is_err", err_res.is_err(), true);
    CHECK("err.is_ok", err_res.is_ok(), false);
    CHECK("err.unwrap_err", err_res.unwrap_err(), 7);
    CHECK("err.unwrap_or", err_res.unwrap_or(99), 99);

    // ── ③ map — 成功分支变换 (result<T,E> → result<U,E>) ───────────
    auto mapped_ok = ok_res.map([](int x) { return x + 1; });
    CHECK("map.on_ok.is_ok", mapped_ok.is_ok(), true);
    CHECK("map.on_ok.unwrap", mapped_ok.unwrap(), 43);

    // ── ④ map_err — 错误分支变换 (result<T,E> → result<T,F>) ────────
    auto mapped_err = err_res.map_err([](int e) { return e * 2; });
    CHECK("map_err.on_err.is_err", mapped_err.is_err(), true);
    CHECK("map_err.on_err.unwrap_err", mapped_err.unwrap_err(), 14);

    // ── ⑤ and_then — 成功分支链式组合（callable 返回新 result） ─────
    // 上游实证：result<u32,u32>{success(2)}.and_then(sq).and_then(sq) == success(16)
    auto sq = [](int x) -> result<int, int> { return success_t<int>{x * x}; };
    auto chained_ok = result<int, int>{success_t<int>{2}}.and_then(sq).and_then(sq);
    CHECK("and_then.on_ok.is_ok", chained_ok.is_ok(), true);
    CHECK("and_then.on_ok.unwrap", chained_ok.unwrap(), 16);

    // ── ⑥ or_else — 错误分支链式组合（callable 返回新 result） ──────
    // 上游实证：result<u32,u32>{failure(3)}.or_else(sq).or_else(err) == success(9)
    auto chained_err = result<int, int>{failure_t<int>{3}}.or_else(sq);
    CHECK("or_else.on_err.is_ok", chained_err.is_ok(), true);
    CHECK("or_else.on_err.unwrap", chained_err.unwrap(), 9);

    // ── ⑦ map 在错误分支上保持错误不变 ───────────────────────────────
    auto mapped_on_err = err_res.map([](int x) { return x + 100; });
    CHECK("map.on_err.is_err", mapped_on_err.is_err(), true);
    CHECK("map.on_err.unwrap_err", mapped_on_err.unwrap_err(), 7);

    // ── ⑧ and_then 在错误分支上保持错误不变 ─────────────────────────
    auto and_then_on_err = err_res.and_then(sq);
    CHECK("and_then.on_err.is_err", and_then_on_err.is_err(), true);
    CHECK("and_then.on_err.unwrap_err", and_then_on_err.unwrap_err(), 7);

    // ── ⑨ or_else 在成功分支上保持成功不变 ──────────────────────────
    auto or_else_on_ok = ok_res.or_else(sq);
    CHECK("or_else.on_ok.is_ok", or_else_on_ok.is_ok(), true);
    CHECK("or_else.on_ok.unwrap", or_else_on_ok.unwrap(), 42);

    // ── ⑩ 成功/错误分支互斥 ─────────────────────────────────────────
    CHECK("ok!=err.is_ok", ok_res.is_ok() != err_res.is_ok(), true);

    // ── 汇总 ────────────────────────────────────────────────────────
    std::cout << "\nRESULT: " << g_checks_total << " CHECK, "
              << g_checks_total << " PASS, 0 FAIL" << std::endl;
    return 0;
}
