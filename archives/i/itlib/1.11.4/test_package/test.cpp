// test_package/test.cpp — itlib 1.11.4 消费者视角真实用例（鸿蒙特有测试行）
//
// 从「已安装的 itlib 包」（package() 交付的 include/itlib/*.hpp）出发，真实调用头文件
// API 并逐条断言行为（R34：非空壳、非 print-only、不是只打印不调用）。
// 任一断言失败 → 打印 ITLIB-CONSUMER 行并以 rc=1 退出 → conan create 失败。
//
// 取数（见 test_package/MANIFEST.yml 的 assertion_count）：
//   本文件 check_true / check_eq_i / check_eq_s / check_throws 的调用点总数
//   = 消费者断言数；运行期以末行 `ITLIB-CONSUMER checks=<N>` 为准。
//
// 覆盖 12 个交付头（头文件库的「可消费性」= 交付物正确性的唯一消费者侧证据）：
//   strutil / qalgorithm / span / small_vector / static_vector / flat_map /
//   dynamic_bitset / any / expected / type_traits / utility / time_t
// 刻意排除 pmr_allocator.hpp：OHOS libc++ 15.0.4 未提供 <memory_resource>
// （上游 t-pmr_allocator-*、t-any-17 三处以 `_LIBCPP_VERSION >= 16000` 自带守卫禁用，
//   见 notes.md「已知限制」）——不在消费者面冒充可消费。
#include <itlib/strutil.hpp>
#include <itlib/qalgorithm.hpp>
#include <itlib/span.hpp>
#include <itlib/small_vector.hpp>
#include <itlib/static_vector.hpp>
#include <itlib/flat_map.hpp>
#include <itlib/dynamic_bitset.hpp>
#include <itlib/any.hpp>
#include <itlib/expected.hpp>
#include <itlib/type_traits.hpp>
#include <itlib/utility.hpp>
#include <itlib/time_t.hpp>

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

static int g_checks = 0;
static int g_failures = 0;

static void check_true(bool cond, const char* what) {
    ++g_checks;
    if (!cond) {
        ++g_failures;
        std::cerr << "[FAIL] " << what << "\n";
    }
}

static void check_eq_i(long long got, long long want, const char* what) {
    ++g_checks;
    if (got != want) {
        ++g_failures;
        std::cerr << "[FAIL] " << what << ": got=" << got << " want=" << want << "\n";
    }
}

static void check_eq_s(const std::string& got, const std::string& want, const char* what) {
    ++g_checks;
    if (got != want) {
        ++g_failures;
        std::cerr << "[FAIL] " << what << ": got=\"" << got << "\" want=\"" << want << "\"\n";
    }
}

class incomplete_type;

int main() {
    // ── 1. strutil：string_view 工具 ─────────────────────────────────────
    {
        const std::string_view x = "start_123_end";
        check_true(itlib::starts_with(x, ""), "starts_with empty prefix");
        check_true(itlib::starts_with(x, "start"), "starts_with prefix");
        check_true(!itlib::starts_with(x, "tart"), "starts_with rejects interior");
        check_true(itlib::ends_with(x, "end"), "ends_with suffix");
        check_true(!itlib::ends_with(x, "en"), "ends_with rejects interior");
        check_eq_s(std::string(itlib::remove_prefix_all("stst_endend", "st")), "_endend",
                   "remove_prefix_all");
        check_eq_s(std::string(itlib::remove_suffix_all("stst_endend", "end")), "stst_",
                   "remove_suffix_all");
        const char* digits = "0123456789";
        check_true(itlib::make_string_view(digits, digits + 3) == "012", "make_string_view");
    }

    // ── 2. qalgorithm：容器上的查询/删除算法 ────────────────────────────
    {
        std::vector<int> vec = {1, 2, 3, 4};
        auto i = itlib::qfind(vec, 3);
        check_true(i != vec.end(), "qfind finds existing element");
        check_eq_i(*i, 3, "qfind value");
        check_eq_i(itlib::qfind(vec, 9) - vec.begin(), 4, "qfind miss returns end");
        check_true(itlib::pfind(vec, 2) != nullptr, "pfind hit");
        check_true(itlib::pfind(vec, 9) == nullptr, "pfind miss");
        check_true(itlib::qall_of(vec), "qall_of all positive");
        check_true(!itlib::qany_of(std::vector<int>{0, 0}), "qany_of none positive");
        check_true(itlib::erase_first(vec, 9) == false, "erase_first miss");
        check_true(itlib::erase_first(vec, 2), "erase_first hit");
        check_eq_i(vec.size(), 3, "erase_first shrinks");
        check_eq_i(itlib::erase_all(vec, 3), 1, "erase_all count");
    }

    // ── 3. span：非拥有视图 ──────────────────────────────────────────────
    {
        std::vector<int> vec = {1, 2, 3, 2, 4};
        itlib::span<int> sp = vec;
        itlib::span<const int> csp = vec;
        check_eq_i(sp.size(), 5, "span size");
        check_eq_i(sp.front(), 1, "span front");
        check_eq_i(sp.back(), 4, "span back");
        check_eq_i(csp.size(), 5, "const span size");
        sp[0] = 42;
        check_eq_i(vec[0], 42, "span aliases underlying storage");
    }

    // ── 4. small_vector：小缓冲区向量 ────────────────────────────────────
    {
        itlib::small_vector<int, 10> sv;
        check_eq_i(sv.size(), 0, "small_vector empty");
        check_eq_i(sv.capacity(), 10, "small_vector inline capacity");
        check_true(sv.empty(), "small_vector empty()");
        check_true(sv.begin() == sv.end(), "small_vector begin==end when empty");
        sv.push_back(8);
        sv.push_back(9);
        check_eq_i(sv.size(), 2, "small_vector size after push");
        check_eq_i(sv.front(), 8, "small_vector front");
        check_eq_i(sv.back(), 9, "small_vector back");
        check_eq_i(sv.capacity(), 10, "small_vector stays inline (no heap growth)");
        const itlib::small_vector<int, 10> init = {1, 2, 3};
        check_eq_i(init.size(), 3, "small_vector init-list");
        check_eq_i(init[2], 3, "small_vector init-list element");
    }

    // ── 5. static_vector：定容容器 ───────────────────────────────────────
    {
        itlib::static_vector<int, 10> stv;
        check_eq_i(stv.capacity(), 10, "static_vector capacity");
        check_eq_i(stv.max_size(), 10, "static_vector max_size");
        stv.push_back(5);
        check_eq_i(stv.size(), 1, "static_vector size");
        check_eq_i(stv[0], 5, "static_vector element");
        check_true(stv.data() == &stv[0], "static_vector data pointer");
    }

    // ── 6. flat_map：有序关联容器 ────────────────────────────────────────
    {
        itlib::flat_map<int, char> fm = {{1, 'a'}, {4, 'd'}, {3, 'c'}};
        check_eq_i(fm.size(), 3, "flat_map size");
        check_true(!fm.empty(), "flat_map not empty");
        check_eq_i(fm.count(1), 1, "flat_map count hit");
        check_eq_i(fm.count(5), 0, "flat_map count miss");
        check_eq_s(std::string(1, fm[1]), "a", "flat_map operator[]");
        check_eq_s(std::string(1, fm.at(3)), "c", "flat_map at");
        bool threw = false;
        try {
            (void)fm.at(0);
        } catch (const std::out_of_range&) {
            threw = true;
        }
        check_true(threw, "flat_map::at throws std::out_of_range for missing key");
        check_eq_i(fm.begin()->first, 1, "flat_map keeps keys sorted");
    }

    // ── 7. dynamic_bitset：动态位图 ──────────────────────────────────────
    {
        using db32 = itlib::dynamic_bitset<std::vector<uint32_t>>;
        check_eq_i(db32::word_size(3), 1, "word_size(3)");
        check_eq_i(db32::word_size(64), 2, "word_size(64)");
        check_eq_i(db32::word_index(63), 1, "word_index(63)");
        check_eq_i(db32::word_mask(3), 0x8, "word_mask(3)");

        db32 bits(70);
        check_eq_i(bits.size(), 70, "dynamic_bitset size");
        check_true(!bits.test(3), "bit starts clear");
        bits.set(3);
        bits.set(69);
        check_true(bits.test(3), "set(3) observable");
        check_true(bits.test(69), "set(69) crosses word boundary");
        bits.reset(3);
        check_true(!bits.test(3), "reset(3) observable");
        bits.set(69, false);
        check_true(!bits.test(69), "set(i,false) observable");
    }

    // ── 8. any：类型擦除容器 ─────────────────────────────────────────────
    {
        itlib::any<> a;
        check_true(!a, "any empty is falsy");
        check_true(!a.has_value(), "any empty has_value()==false");
        itlib::any<> b = std::string("foo bar");
        check_true(!!b, "any with value is truthy");
        check_true(b.tdata<std::string>() != nullptr, "any tdata type match");
        check_eq_s(*b.tdata<std::string>(), "foo bar", "any stored value");
        itlib::any<> c = b;
        check_eq_s(*c.tdata<std::string>(), "foo bar", "any copy preserves value");
        b.reset();
        check_true(!b, "any reset clears");
        check_eq_s(*c.tdata<std::string>(), "foo bar", "any copy independent of source");
    }

    // ── 9. expected：值/错误二态返回 ─────────────────────────────────────
    {
        itlib::expected<int, int> ok;
        check_true(!!ok, "expected default-constructed has value");
        check_true(ok.has_value(), "expected has_value");
        check_eq_i(ok.value(), 0, "expected default value");
        check_eq_i(ok.value_or(74), 0, "expected value_or uses value");
        itlib::expected<int, int> v = 123;
        check_eq_i(*v, 123, "expected dereference");
        check_eq_i(v.value_or(74), 123, "expected value_or non-empty");
        itlib::expected<int, int> e = itlib::unexpected(7);
        check_true(!e, "expected error is falsy");
        check_true(e.has_error(), "expected has_error");
        check_eq_i(e.error(), 7, "expected error payload");
        check_eq_i(e.value_or(74), 74, "expected value_or fallback");
    }

    // ── 11. type_traits：编译期元函数（运行期复核其值）─────────────────
    {
        using veci = std::vector<int>;
        check_true(itlib::is_instantiation_of<std::vector, veci>::value,
                   "is_instantiation_of positive");
        check_true(!itlib::is_instantiation_of<std::vector, int>::value,
                   "is_instantiation_of negative");
        check_true(itlib::type_identity<int>::type() == 0, "type_identity yields the type");
        check_true(itlib::is_noop_convertible<int, int>::value, "is_noop_convertible same type");
        check_true(itlib::is_noop_convertible<int, unsigned>::value,
                   "is_noop_convertible same binary representation");
        check_true(!itlib::is_noop_convertible<int, double>::value,
                   "is_noop_convertible rejects different representation");
    }

    // ── 12. utility：force_move / make_nullptr ───────────────────────────
    {
        check_eq_i(itlib::force_move(7), 7, "force_move keeps value");
        check_eq_s(itlib::force_move(std::string("str")), "str", "force_move on rvalue");
        auto p = itlib::make_nullptr<incomplete_type>();
        check_true(p == nullptr, "make_nullptr on incomplete type");
    }

    // ── 13. time_t：时间点运算与 UTC 分解（不依赖 locale）──────────────
    {
        itlib::time_t t(100);
        check_eq_i(t.seconds_since_epoch(), 100, "time_t seconds_since_epoch");
        auto sum = t + std::chrono::milliseconds(1800);
        check_eq_i(sum.seconds_since_epoch(), 101, "time_t + 1800ms");
        check_true(sum > t, "time_t ordering");
        auto diff = itlib::time_t(200) - t;
        check_eq_i(diff.count(), 100, "time_t difference");
        auto tm = itlib::time_t(1000100000).gmtime();
        check_eq_i(tm.tm_year, 101, "time_t gmptime tm_year");
        check_eq_i(tm.tm_mday, 10, "time_t gmtime tm_mday");
        check_eq_i(tm.tm_hour, 5, "time_t gmtime tm_hour");
    }

    std::cout << "ITLIB-CONSUMER checks=" << g_checks
              << " failures=" << g_failures << std::endl;
    return g_failures == 0 ? 0 : 1;
}
