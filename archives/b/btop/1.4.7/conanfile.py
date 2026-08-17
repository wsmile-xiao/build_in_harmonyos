import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file, save
from conan.tools.layout import basic_layout


_EXPECTED_FALLBACK = r"""#pragma once
#if __has_include(<expected>) && !defined(BTOP_FORCE_EXPECTED_FALLBACK)
#include <expected>
#else
#include <utility>

namespace std {
template <class E>
class unexpected {
public:
    constexpr explicit unexpected(E value) : value_(std::move(value)) {}
    constexpr const E& error() const & noexcept { return value_; }
    constexpr E& error() & noexcept { return value_; }
private:
    E value_;
};

template <class T, class E>
class expected {
public:
    constexpr expected(const T& value) : has_(true), value_(value), error_() {}
    constexpr expected(T&& value) : has_(true), value_(std::move(value)), error_() {}
    constexpr expected(const unexpected<E>& error) : has_(false), value_(), error_(error.error()) {}
    constexpr expected(unexpected<E>&& error) : has_(false), value_(), error_(std::move(error.error())) {}
    constexpr bool has_value() const noexcept { return has_; }
    constexpr explicit operator bool() const noexcept { return has_; }
    constexpr T& value() & noexcept { return value_; }
    constexpr const T& value() const & noexcept { return value_; }
    constexpr E& error() & noexcept { return error_; }
    constexpr const E& error() const & noexcept { return error_; }
private:
    bool has_ {};
    T value_ {};
    E error_ {};
};
}  // namespace std
#endif
"""


_GTEST_STUB = r"""#pragma once
#include <cstdlib>
#include <exception>
#include <functional>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace testing {
struct TestCase {
    const char* suite;
    const char* name;
    void (*func)();
};

inline std::vector<TestCase>& registry() {
    static auto* tests = new std::vector<TestCase>();
    return *tests;
}

inline int& failure_count() {
    static auto* failures = new int(0);
    return *failures;
}

inline int register_test(const char* suite, const char* name, void (*func)()) {
    registry().push_back(TestCase{suite, name, func});
    return 0;
}

inline void fail(const char* file, int line, const char* expr) {
    ++failure_count();
    std::cerr << file << ":" << line << ": EXPECT_EQ failed: " << expr << "\n";
}

inline int RunAllTests() {
    for (const auto& test : registry()) {
        std::cout << "[ RUN      ] " << test.suite << "." << test.name << "\n";
        const auto before = failure_count();
        try {
            test.func();
        } catch (const std::exception& e) {
            ++failure_count();
            std::cerr << "[ EXCEPTION] " << test.suite << "." << test.name << ": " << e.what() << "\n";
        } catch (...) {
            ++failure_count();
            std::cerr << "[ EXCEPTION] " << test.suite << "." << test.name << ": unknown exception\n";
        }
        std::cout << (failure_count() == before ? "[       OK ] " : "[  FAILED  ] ")
                  << test.suite << "." << test.name << "\n";
    }
    std::cout << "[==========] " << registry().size() << " upstream test(s) ran.\n";
    if (failure_count() == 0) {
        std::cout << "=== btop upstream tests PASSED ===\n";
    }
    return failure_count() == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
}  // namespace testing

#define TEST(SUITE, NAME) \
    static void SUITE##_##NAME##_Test(); \
    static int SUITE##_##NAME##_registered = ::testing::register_test(#SUITE, #NAME, &SUITE##_##NAME##_Test); \
    static void SUITE##_##NAME##_Test()

#define EXPECT_EQ(A, B) \
    do { \
        const auto& _btop_test_lhs = (A); \
        const auto& _btop_test_rhs = (B); \
        if (!(_btop_test_lhs == _btop_test_rhs)) { \
            ::testing::fail(__FILE__, __LINE__, #A " == " #B); \
        } \
    } while (0)
"""


_GTEST_MAIN = r"""#include <gtest/gtest.h>

int main() {
    return testing::RunAllTests();
}
"""


# clang-15 libc++ lacks std::ranges::* algorithms (C++20 ranges adaptors exist, but
# std::ranges::find/find_if/all_of/any_of/count/count_if/transform/sort/stable_sort/
# equal_range/remove_if/distance/empty/for_each do not). btop 1.4.7 uses these via `rng::*`
# (alias of std::ranges) and std::ranges::* across ~130 sites with projections.
# This shim implements the missing algorithms by delegating to the classic std::* in
# <algorithm> with projection support, so upstream call sites compile unmodified.
_RANGES_SHIM = r"""#pragma once
#include <algorithm>
#include <functional>
#include <iterator>
#include <ranges>
#include <type_traits>
#include <utility>

namespace std::ranges {

// btop_draw.cpp does `using std::views::iota;` then bare `iota(a,b)`; clang-15 libc++ has no views::iota.
// Provide a minimal iota producing an iterable range [start, end).
namespace _detail {
template <class T> struct _iota_range {
    T first_, last_;
    struct iterator {
        T v; using iterator_category = std::input_iterator_tag; using value_type = T; using difference_type = std::ptrdiff_t; using pointer = void; using reference = T;
        iterator& operator++() { ++v; return *this; } iterator operator++(int) { auto t=*this; ++v; return t; }
        reference operator*() const { return v; } bool operator!=(const iterator& o) const { return v != o.v; } bool operator==(const iterator& o) const { return v == o.v; }
    };
    iterator begin() const { return {first_}; } iterator end() const { return {last_}; }
};
}  // namespace _detail

namespace views {
template <class T1, class T2> auto iota(T1 start, T2 end) { using V = common_type_t<T1, T2>; return _detail::_iota_range<V>{static_cast<V>(start), static_cast<V>(end)}; }
}  // namespace views

}  // namespace std::ranges

// btop_draw.cpp: `using std::views::iota;` — alias std::views to our shim's views.
namespace std { namespace views = ::std::ranges::views; }

namespace std::ranges {

namespace _detail {
template <class T> using _iter_ref_t = typename iterator_traits<decay_t<decltype(std::begin(std::declval<T&>()))>>::reference;
struct _identity { template <class V> constexpr V&& operator()(V&& v) const noexcept { return std::forward<V>(v); } };
template <class P, class... Args> auto _invoke_proj(P&& p, Args&&... a) -> decltype(auto) {
    if constexpr (is_member_pointer_v<decay_t<P>>) return std::invoke(p, std::forward<Args>(a)...);
    else return std::forward<P>(p)(std::forward<Args>(a)...);
}
}  // namespace _detail

template <class R, class T>
auto find(R&& r, const T& v) {
    return std::find(std::begin(r), std::end(r), v);
}
template <class R, class T, class P>
auto find(R&& r, const T& v, P proj) {
    auto it = std::begin(r);
    auto en = std::end(r);
    for (; it != en; ++it) { if (_detail::_invoke_proj(proj, *it) == v) return it; }
    return it;
}

template <class R, class F>
auto find_if(R&& r, F f) {
    return std::find_if(std::begin(r), std::end(r), f);
}

template <class R, class F>
bool all_of(R&& r, F f) { return std::all_of(std::begin(r), std::end(r), f); }
template <class R, class F>
bool any_of(R&& r, F f) { return std::any_of(std::begin(r), std::end(r), f); }
template <class R, class F>
auto count_if(R&& r, F f) { return std::count_if(std::begin(r), std::end(r), f); }
template <class R, class T>
auto count(R&& r, const T& v) { return std::count(std::begin(r), std::end(r), v); }

template <class R, class F>
void for_each(R&& r, F f) { std::for_each(std::begin(r), std::end(r), f); }

// transform: support (range, range, out, binary), (range, out, unary), and iterator forms.
// The range overloads must win when a container (e.g. std::deque) is passed where an iterator is expected.
template <class R1, class R2, class O, class F,
          class = enable_if_t<!is_same_v<decay_t<R1>, decay_t<R2>> || is_same_v<decay_t<R1>, decay_t<R2>>>>
O transform(R1&& r1, R2&& r2, O out, F f) {
    return std::transform(std::begin(r1), std::end(r1), std::begin(r2), out, f);
}
template <class R, class O, class F>
O transform(R&& r, O out, F f) {
    return std::transform(std::begin(r), std::end(r), out, f);
}
// iterator form: (first1, last1, first2, out, binary)
template <class I1, class I2, class O, class F,
          class = enable_if_t<is_base_of_v<std::input_iterator_tag, typename std::iterator_traits<decay_t<I1>>::iterator_category>>>
O transform(I1 first1, I1 last1, I2 first2, O out, F f) {
    return std::transform(first1, last1, first2, out, f);
}

template <class R, class C = std::less<>, class P = _detail::_identity>
void sort(R&& r, C comp = C{}, P proj = P{}) {
    if constexpr (is_same_v<P, _detail::_identity>) std::sort(std::begin(r), std::end(r), comp);
    else std::sort(std::begin(r), std::end(r), [&](auto&& a, auto&& b) { return comp(_detail::_invoke_proj(proj, a), _detail::_invoke_proj(proj, b)); });
}
template <class R, class C = std::less<>, class P = _detail::_identity>
void stable_sort(R&& r, C comp = C{}, P proj = P{}) {
    if constexpr (is_same_v<P, _detail::_identity>) std::stable_sort(std::begin(r), std::end(r), comp);
    else std::stable_sort(std::begin(r), std::end(r), [&](auto&& a, auto&& b) { return comp(_detail::_invoke_proj(proj, a), _detail::_invoke_proj(proj, b)); });
}

// equal_range returns std::pair<iter,iter> which isn't iterable pre-C++23 libc++.
// Wrap it so `for (auto& p : rng::equal_range(...))` works.
template <class I>
struct _iter_pair {
    I first_, last_;
    I begin() const { return first_; } I end() const { return last_; }
};

template <class R, class T, class C = std::less<>, class P = _detail::_identity>
auto equal_range(R&& r, const T& v, C comp = C{}, P proj = P{}) {
    if constexpr (is_same_v<P, _detail::_identity>) {
        auto p = std::equal_range(std::begin(r), std::end(r), v, comp);
        return _iter_pair<decltype(p.first)>{p.first, p.second};
    } else {
        auto p = std::equal_range(std::begin(r), std::end(r), v, [&](const auto& a, const auto& b) {
            using A = decay_t<decltype(a)>; using B = decay_t<decltype(b)>;
            if constexpr (is_same_v<A, T> && is_same_v<B, T>) return comp(a, b);
            else if constexpr (is_same_v<A, T>) return comp(a, _detail::_invoke_proj(proj, b));
            else if constexpr (is_same_v<B, T>) return comp(_detail::_invoke_proj(proj, a), b);
            else return comp(_detail::_invoke_proj(proj, a), _detail::_invoke_proj(proj, b));
        });
        return _iter_pair<decltype(p.first)>{p.first, p.second};
    }
}

template <class R, class F>
auto remove_if(R&& r, F f) { return std::remove_if(std::begin(r), std::end(r), f); }

template <class R>
auto distance(R&& r) { return std::distance(std::begin(r), std::end(r)); }
template <class I, class S>
auto distance(I first, S last) { return std::distance(first, last); }

template <class R>
bool empty(R&& r) {
    if constexpr (requires { r.empty(); }) return r.empty();
    else return std::begin(r) == std::end(r);
}

}  // namespace std::ranges
"""


class BtopConan(ConanFile):
    name = "btop"
    version = "1.4.7"
    description = "Resource monitor that shows CPU, memory, disk, network and process information"
    license = "Apache-2.0"
    homepage = "https://github.com/aristocratos/btop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("btop supports Linux/OHOS only in this recipe")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self._patch_ohos()
        cxx = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "c++")
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        shim = os.path.join(self.source_folder, "include", "btop_ranges_shim.hpp")
        cxxflags = "-DBTOP_FORCE_EXPECTED_FALLBACK -DBTOP_OHOS -include {} -I {}".format(shlex.quote(shim), shlex.quote(os.path.join(self.source_folder, "include")))
        args = [
            "make",
            "PLATFORM=linux",
            "GPU_SUPPORT=false",
            "INTEL_GPU_SUPPORT=false",
            "STATIC=false",
            "STRIP=false",
            "QUIET=true",
            "VERBOSE=false",
            "THREADS=1",
            "BUILD_TYPE=Release",
            "CXX={}".format(shlex.quote(cxx)),
            "CC={}".format(shlex.quote(cc)),
            "ADDFLAGS={}".format(shlex.quote(cxxflags)),
            "-j1",
        ]
        self.run(" ".join(args), cwd=self.source_folder, env="conanbuild")
        self._run_upstream_tests(cxx, cxxflags)

    def _run_upstream_tests(self, cxx, cxxflags):
        save(self, os.path.join(self.source_folder, "include", "gtest", "gtest.h"), _GTEST_STUB)
        test_main = os.path.join(self.build_folder, "btop_upstream_test_main.cpp")
        test_bin = os.path.join(self.build_folder, "btop_upstream_tests")
        save(self, test_main, _GTEST_MAIN)
        args = [
            shlex.quote(cxx),
            "-std=gnu++2b",
            "-O2",
            "-ffunction-sections",
            "-fdata-sections",
            "-I{}".format(shlex.quote(os.path.join(self.source_folder, "include"))),
            "-I{}".format(shlex.quote(os.path.join(self.source_folder, "src"))),
            cxxflags,
            "tests/cpu_names.cpp",
            "tests/tools.cpp",
            "src/btop_shared.cpp",
            "src/btop_tools.cpp",
            shlex.quote(test_main),
            "-Wl,--gc-sections",
            "-pthread",
            "-o",
            shlex.quote(test_bin),
        ]
        self.run(" ".join(args), cwd=self.source_folder, env="conanbuild")
        self.run(shlex.quote(test_bin), cwd=self.source_folder, env="conanbuild")

    def _patch_ohos(self):
        save(self, os.path.join(self.source_folder, "include", "btop_expected_fallback.hpp"), _EXPECTED_FALLBACK)
        # clang-15 libc++ lacks std::ranges::* algorithms; this shim implements them by delegating to
        # the classic std::* in <algorithm>. Force-included via ADDFLAGS, so upstream call sites stay as-is.
        save(self, os.path.join(self.source_folder, "include", "btop_ranges_shim.hpp"), _RANGES_SHIM)
        # clang-15 (OHOS toolchain) does not accept -std=c++23; use gnu++2b (C++23 draft) instead.
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(
            self,
            makefile,
            "override REQFLAGS   := -std=c++23",
            "override REQFLAGS   := -std=gnu++2b",
            strict=False,
        )
        # btop_tools.hpp gates BTOP_DEBUG on !NDEBUG; libc++ on clang-15 lacks <source_location>,
        # so disable BTOP_DEBUG under BTOP_OHOS to avoid the missing header.
        tools_header = os.path.join(self.source_folder, "src", "btop_tools.hpp")
        replace_in_file(
            self,
            tools_header,
            "#if !defined(NDEBUG)\n# define BTOP_DEBUG\n#endif",
            "#if !defined(NDEBUG) && !defined(BTOP_OHOS)\n# define BTOP_DEBUG\n#endif",
            strict=False,
        )
        # clang-15 libc++ lacks std::ranges::* algorithms; fall back to classic std:: equivalents.
        replace_in_file(
            self,
            tools_header,
            "return (wide ? wide_ulen(str) : std::ranges::count_if(str, [](char c) { return (static_cast<unsigned char>(c) & 0xC0) != 0x80; }));",
            "return (wide ? wide_ulen(str) : static_cast<size_t>(std::count_if(str.begin(), str.end(), [](char c) { return (static_cast<unsigned char>(c) & 0xC0) != 0x80; })));",
            strict=False,
        )
        replace_in_file(
            self,
            tools_header,
            "std::ranges::for_each(str, [](auto& c) { c = ::toupper(c); } );",
            "std::for_each(str.begin(), str.end(), [](auto& c) { c = ::toupper(c); } );",
            strict=False,
        )
        replace_in_file(
            self,
            tools_header,
            "std::ranges::for_each(str, [](char& c) { c = ::tolower(c); } );",
            "std::for_each(str.begin(), str.end(), [](char& c) { c = ::tolower(c); } );",
            strict=False,
        )
        replace_in_file(
            self,
            tools_header,
            "return std::ranges::find(vec, find_val) != vec.end();",
            "return std::find(vec.begin(), vec.end(), find_val) != vec.end();",
            strict=False,
        )
        replace_in_file(
            self,
            tools_header,
            "return std::ranges::distance(vec.begin(), std::ranges::find(vec, find_val));",
            "return static_cast<size_t>(std::distance(vec.begin(), std::find(vec.begin(), vec.end(), find_val)));",
            strict=False,
        )
        replace_in_file(
            self,
            tools_header,
            "return std::ranges::all_of(str, ::isdigit);",
            "return std::all_of(str.begin(), str.end(), ::isdigit);",
            strict=False,
        )
        cli_header = os.path.join(self.source_folder, "src", "btop_cli.hpp")
        replace_in_file(
            self,
            cli_header,
            "#include <expected>",
            "#include <btop_expected_fallback.hpp>",
            strict=False,
        )
        cli_cpp = os.path.join(self.source_folder, "src", "btop_cli.cpp")
        replace_in_file(
            self,
            cli_cpp,
            "#include <expected>",
            "#include <btop_expected_fallback.hpp>",
            strict=False,
        )
        # btop_cli.cpp uses std::views::split to iterate config lines; clang-15 libc++ lacks std::views.
        replace_in_file(
            self,
            cli_cpp,
            "\t\t\tauto trimmed_config = config.substr(0, config.length() - 1);\n\t\t\tfor (const auto line : std::views::split(trimmed_config, '\\n')) {",
            "\t\t\tauto trimmed_config = config.substr(0, config.length() - 1);\n\t\t\tsize_t _pos = 0;\n\t\t\twhile (_pos < trimmed_config.size()) {\n\t\t\t\tauto _next = trimmed_config.find('\\n', _pos);\n\t\t\t\tif (_next == std::string::npos) _next = trimmed_config.size();\n\t\t\t\tstd::string_view line(trimmed_config.data() + _pos, _next - _pos);\n\t\t\t\t_pos = _next + 1;",
            strict=False,
        )
        # btop_config.cpp uses rng::find_if / rng::find (alias of std::ranges); replace with std:: equivalents.
        config_cpp = os.path.join(self.source_folder, "src", "btop_config.cpp")
        replace_in_file(
            self,
            config_cpp,
            "if (not write_new and rng::find_if(descriptions, [&name](const auto& a) { return a.at(0) == name; }) != descriptions.end())",
            "if (not write_new and std::find_if(descriptions.begin(), descriptions.end(), [&name](const auto& a) { return a.at(0) == name; }) != descriptions.end())",
            strict=False,
        )
        replace_in_file(
            self,
            config_cpp,
            "auto box_pos = rng::find(current_boxes, box);",
            "auto box_pos = std::find(current_boxes.begin(), current_boxes.end(), box);",
            strict=False,
        )
        # clang-15 libc++ std::optional<fs::path> is not a literal type; drop constexpr on get_xdg_state_dir.
        replace_in_file(
            self,
            config_cpp,
            "static constexpr auto get_xdg_state_dir() -> std::optional<fs::path> {",
            "static auto get_xdg_state_dir() -> std::optional<fs::path> {",
            strict=False,
        )
        tools_header = os.path.join(self.source_folder, "src", "btop_tools.hpp")
        replace_in_file(
            self,
            tools_header,
            """\t//* Split <string> at all occurrences of <delim> and return as vector of strings
\tconstexpr auto ssplit(std::string_view str, char delim = ' ') {
\t\treturn str | std::views::split(delim) | std::views::filter([](auto&& range) { return !std::ranges::empty(range); }) |
\t\t\t   std::ranges::to<std::vector<std::string>>();
\t}
""",
            """\t//* Split <string> at all occurrences of <delim> and return as vector of strings
\tinline auto ssplit(std::string_view str, char delim = ' ') {
\t\tstd::vector<std::string> out;
\t\tsize_t pos = 0;
\t\twhile (pos <= str.size()) {
\t\t\tsize_t next = str.find(delim, pos);
\t\t\tif (next == std::string_view::npos) next = str.size();
\t\t\tif (next > pos) out.emplace_back(str.substr(pos, next - pos));
\t\t\tpos = next + 1;
\t\t}
\t\treturn out;
\t}
""",
            strict=False,
        )
        main_cpp = os.path.join(self.source_folder, "src", "main.cpp")
        replace_in_file(
            self,
            main_cpp,
            """auto main(int argc, const char* argv[]) -> int {
\treturn btop_main(std::views::counted(std::next(argv), argc - 1) | std::ranges::to<std::vector<std::string_view>>());
}
""",
            """auto main(int argc, const char* argv[]) -> int {
\tstd::vector<std::string_view> args;
\targs.reserve(argc > 0 ? static_cast<std::size_t>(argc - 1) : 0);
\tfor (int i = 1; i < argc; ++i) args.emplace_back(argv[i]);
\treturn btop_main(args);
}
""",
            strict=False,
        )
        linux_collect = os.path.join(self.source_folder, "src", "linux", "btop_collect.cpp")
        # detect_active_cpus() uses the same iota|ranges::to string as the cpus patch below;
        # replace the WHOLE function first so the later iota patch still finds its target.
        replace_in_file(
            self,
            linux_collect,
            """    static constexpr auto detect_active_cpus() {
        auto stream = std::ifstream { "/sys/fs/cgroup/cpuset.cpus.effective" };
        auto buf = std::string { std::istreambuf_iterator<char> { stream }, {} };

        if (buf.empty()) {
            return std::views::iota(0, Shared::coreCount) | std::ranges::to<std::vector<std::int32_t>>();
        }

        return buf | std::views::split(',') | std::views::transform([](auto&& range) -> auto {
                   auto view = std::string_view { range };
                   auto dash = view.find('-');

                   if (dash == std::string_view::npos) {
                       // Single CPU, return iota of single element
                       auto value = to_int(view);
                       return std::views::iota(value, value + 1);
                   }

                   auto start = to_int(view.substr(0, dash));
                   auto end = to_int(view.substr(dash + 1));
                   return std::views::iota(start, end + 1);
               }) |
               std::views::join | std::ranges::to<std::vector<std::int32_t>>();
    }
""",
            """    static auto detect_active_cpus() {
        auto stream = std::ifstream { "/sys/fs/cgroup/cpuset.cpus.effective" };
        auto buf = std::string { std::istreambuf_iterator<char> { stream }, {} };

        if (buf.empty()) {
            auto cpus = std::vector<std::int32_t>{};
            for (int i = 0; i < Shared::coreCount; ++i) cpus.push_back(i);
            return cpus;
        }

        auto cpus = std::vector<std::int32_t>{};
        size_t pos = 0;
        while (pos < buf.size()) {
            size_t comma = buf.find(',', pos);
            std::string_view view = (comma == std::string::npos)
                ? std::string_view(buf.data() + pos, buf.size() - pos)
                : std::string_view(buf.data() + pos, comma - pos);
            auto dash = view.find('-');
            if (dash == std::string_view::npos) {
                cpus.push_back(static_cast<std::int32_t>(to_int(view)));
            } else {
                auto start = to_int(view.substr(0, dash));
                auto end = to_int(view.substr(dash + 1));
                for (auto value = start; value <= end; ++value) cpus.push_back(static_cast<std::int32_t>(value));
            }
            if (comma == std::string::npos) break;
            pos = comma + 1;
        }
        return cpus;
    }
""",
            strict=False,
        )
        btop_cpp = os.path.join(self.source_folder, "src", "btop.cpp")
        replace_in_file(
            self,
            btop_cpp,
            """\t#if defined __APPLE__ || defined __OpenBSD__ || defined __NetBSD__
\t\tif (pthread_join(Runner::runner_id, nullptr) != 0) {
\t\t\tLogger::warning("Failed to join _runner thread on exit!");
\t\t\tpthread_cancel(Runner::runner_id);
\t\t}
\t#else
\t\tconstexpr struct timespec ts { .tv_sec = 5, .tv_nsec = 0 };
\t\tif (pthread_timedjoin_np(Runner::runner_id, nullptr, &ts) != 0) {
\t\t\tLogger::warning("Failed to join _runner thread on exit!");
\t\t\tpthread_cancel(Runner::runner_id);
\t\t}
\t#endif
""",
            """\t#if defined __APPLE__ || defined __OpenBSD__ || defined __NetBSD__ || defined BTOP_OHOS
\t\tif (pthread_join(Runner::runner_id, nullptr) != 0) {
\t\t\tLogger::warning("Failed to join _runner thread on exit!");
\t\t}
\t#else
\t\tconstexpr struct timespec ts { .tv_sec = 5, .tv_nsec = 0 };
\t\tif (pthread_timedjoin_np(Runner::runner_id, nullptr, &ts) != 0) {
\t\t\tLogger::warning("Failed to join _runner thread on exit!");
\t\t\tpthread_cancel(Runner::runner_id);
\t\t}
\t#endif
""",
            strict=False,
        )
        replace_in_file(
            self,
            btop_cpp,
            """\t\tif (active) {
\t\t\tLogger::error("Stall in Runner thread, restarting!");
\t\t\tset_active(false);
\t\t\t// exit(1);
\t\t\tpthread_cancel(Runner::runner_id);

\t\t\t// Wait for the thread to actually terminate before creating a new one
\t\t\tvoid* thread_result;
\t\t\tint join_result = pthread_join(Runner::runner_id, &thread_result);
\t\t\tif (join_result != 0) {
\t\t\t\tLogger::warning("Failed to join cancelled thread: {}", strerror(join_result));
\t\t\t}

\t\t\tif (pthread_create(&Runner::runner_id, nullptr, &Runner::_runner, nullptr) != 0) {
\t\t\t\tGlobal::exit_error_msg = "Failed to re-create _runner thread!";
\t\t\t\tclean_quit(1);
\t\t\t}
\t\t}
""",
            """\t\tif (active) {
\t\t\tLogger::error("Stall in Runner thread, restarting!");
\t\t\tset_active(false);
\t\t\t// exit(1);
\t\t#ifndef BTOP_OHOS
\t\t\tpthread_cancel(Runner::runner_id);

\t\t\t// Wait for the thread to actually terminate before creating a new one
\t\t\tvoid* thread_result;
\t\t\tint join_result = pthread_join(Runner::runner_id, &thread_result);
\t\t\tif (join_result != 0) {
\t\t\t\tLogger::warning("Failed to join cancelled thread: {}", strerror(join_result));
\t\t\t}

\t\t\tif (pthread_create(&Runner::runner_id, nullptr, &Runner::_runner, nullptr) != 0) {
\t\t\t\tGlobal::exit_error_msg = "Failed to re-create _runner thread!";
\t\t\t\tclean_quit(1);
\t\t\t}
\t\t#endif
\t\t}
""",
            strict=False,
        )
        # clang-15 libc++ does not allow lambda-capturing a structured-binding name
        # (`auto &[mountpoint, disk] = *it;`). Bind it to a local first.
        replace_in_file(
            self,
            linux_collect,
            """				for (auto it = disks.begin(); it != disks.end(); ) {
					auto &[mountpoint, disk] = *it;
""",
            """				for (auto it = disks.begin(); it != disks.end(); ) {
					auto &[mountpoint_ref, disk] = *it;
					const string mountpoint = mountpoint_ref;
""",
            strict=False,
        )
        # our rng::remove_if shim returns a plain iterator (std::remove_if), not a subrange;
        # fix the call site that assumes the C++20 ranges::remove_if return type.
        replace_in_file(
            self,
            linux_collect,
            """				auto eraser = rng::remove_if(current_procs, [&](const auto& element){ return not v_contains(found, element.pid); });
				current_procs.erase(eraser.begin(), eraser.end());
""",
            """				auto eraser = rng::remove_if(current_procs, [&](const auto& element){ return not v_contains(found, element.pid); });
				current_procs.erase(eraser, current_procs.end());
""",
            strict=False,
        )

    def package(self):
        cxx = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "c++")
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        shim = os.path.join(self.source_folder, "include", "btop_ranges_shim.hpp")
        cxxflags = "-DBTOP_FORCE_EXPECTED_FALLBACK -DBTOP_OHOS -include {} -I {}".format(shlex.quote(shim), shlex.quote(os.path.join(self.source_folder, "include")))
        args = [
            "make",
            "install",
            "PREFIX=/usr/local",
            "DESTDIR={}".format(shlex.quote(self.package_folder)),
            "PLATFORM=linux",
            "GPU_SUPPORT=false",
            "INTEL_GPU_SUPPORT=false",
            "STATIC=false",
            "STRIP=false",
            "QUIET=true",
            "VERBOSE=false",
            "THREADS=1",
            "BUILD_TYPE=Release",
            "CXX={}".format(shlex.quote(cxx)),
            "CC={}".format(shlex.quote(cc)),
            "ADDFLAGS={}".format(shlex.quote(cxxflags)),
        ]
        self.run(" ".join(args), cwd=self.source_folder, env="conanbuild")
        # make install PREFIX=/usr/local lays out usr/local/bin/btop; relocate to Conan's bin/ so
        # package_info's bindirs=["bin"] and runenv PATH resolve correctly.
        src_bin = os.path.join(self.package_folder, "usr", "local", "bin", "btop")
        dst_bin = os.path.join(self.package_folder, "bin", "btop")
        os.makedirs(os.path.dirname(dst_bin), exist_ok=True)
        shutil.move(src_bin, dst_bin)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
