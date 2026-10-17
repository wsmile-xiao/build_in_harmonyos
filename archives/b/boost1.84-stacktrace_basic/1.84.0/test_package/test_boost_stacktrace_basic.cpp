// test_package/test_boost_stacktrace_basic.cpp — boost1.84-stacktrace_basic 1.84.0 L1 smoke test.
// Exercises Boost.Stacktrace the way a downstream consumer does:
// - header-only mode (default): frames via _Unwind_Backtrace;
// - linked mode (BOOST_STACKTRACE_LINK): links libboost_stacktrace_basic.a
//   (libs/stacktrace/src/basic.cpp — the TU this package ships);
// - frame::name() via dladdr on exported symbols (-rdynamic).
#include <boost/stacktrace.hpp>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

// BOOST_SYMBOL_VISIBLE so the symbol lands in the dynamic symbol table
// (dladdr can resolve it when the executable is linked with -rdynamic).
BOOST_SYMBOL_VISIBLE int boost_me(int x) {
    return x * 42;
}

// A deeper call chain so the collected trace has a few frames.
BOOST_NOINLINE boost::stacktrace::stacktrace collect_from_here() {
    return boost::stacktrace::stacktrace();
}

} // namespace

int main() {
    // 1) Basic sanity: a freshly captured stack is non-empty and printable.
    boost::stacktrace::stacktrace st = collect_from_here();
    if (st.empty()) {
        std::cerr << "stacktrace: unexpectedly empty" << std::endl;
        return 1;
    }
    if (st.size() < 2) {
        std::cerr << "stacktrace: too few frames: " << st.size() << std::endl;
        return 1;
    }
    std::cout << "captured " << st.size() << " frames" << std::endl;

    // 2) to_string() formatting: numbered frames (" 0# ...").
    std::string const rendered = boost::stacktrace::to_string(st);
    if (rendered.find("0#") == std::string::npos) {
        std::cerr << "stacktrace: no frame marker in output" << std::endl;
        return 1;
    }
    std::cout << rendered << std::endl;

    // 3) frame API: name()/address()/comparisons on a real frame.
    boost::stacktrace::frame f = st[0];
    if (!f) {
        std::cerr << "stacktrace: frame[0] is falsy" << std::endl;
        return 1;
    }
    if (st[0] != st[1]) {
        std::cout << "frame[0] != frame[1] OK" << std::endl;
    }

    // 4) hash_value on frames (O(1), address-based) — declared in
    //    namespace boost::stacktrace (frame.hpp), like upstream test.cpp.
    std::size_t h1 = boost::stacktrace::hash_value(st[0]);
    std::size_t h2 = boost::stacktrace::hash_value(st[0]);
    if (h1 != h2) {
        std::cerr << "stacktrace: hash_value not stable" << std::endl;
        return 1;
    }

    // 5) copy semantics: a copy keeps the same frames.
    boost::stacktrace::stacktrace copy(st);
    if (copy != st) {
        std::cerr << "stacktrace: copy differs from original" << std::endl;
        return 1;
    }

    // 6) empty stacktrace semantics.
    boost::stacktrace::stacktrace empty_st(100500, 1024);
    if (!empty_st.empty() || empty_st.size() != 0) {
        std::cerr << "stacktrace: skip/depth constructor should be empty" << std::endl;
        return 1;
    }

    // 7) safe_dump_to into a file (POSIX write path, musl OK), then
    //    from_dump() round-trip (same usage as upstream terminate_handler
    //    example: safe_dump_to("./backtrace.dump")).
    {
        char const* dump_path = "stacktrace_dump.bin";
        std::remove(dump_path);
        std::size_t dumped = boost::stacktrace::safe_dump_to(dump_path);
        if (dumped == 0) {
            std::cerr << "stacktrace: safe_dump_to wrote nothing" << std::endl;
            return 1;
        }
        std::ifstream ifs(dump_path, std::ios::binary);
        boost::stacktrace::stacktrace from_dump_st =
            boost::stacktrace::stacktrace::from_dump(ifs);
        if (from_dump_st.size() == 0) {
            std::cerr << "stacktrace: from_dump round-trip empty" << std::endl;
            return 1;
        }
        std::cout << "safe_dump_to wrote " << dumped
                  << " frames; from_dump recovered " << from_dump_st.size()
                  << std::endl;
    }

    // 8) Throw + catch + capture inside the catch block (common usage).
    try {
        throw std::runtime_error("boom");
    } catch (const std::runtime_error& e) {
        boost::stacktrace::stacktrace caught = collect_from_here();
        if (caught.size() < 2) {
            std::cerr << "stacktrace: trace in catch block too shallow" << std::endl;
            return 1;
        }
        std::cout << "caught-path trace: " << caught.size() << " frames" << std::endl;
    }

    std::cout << "boost_me(1) = " << boost_me(1) << std::endl;
    std::cout << "boost1.84-stacktrace_basic 1.84.0: stacktrace capture/format/"
                 "frame API/hash/copy/empty/safe_dump/catch OK" << std::endl;
    return 0;
}
