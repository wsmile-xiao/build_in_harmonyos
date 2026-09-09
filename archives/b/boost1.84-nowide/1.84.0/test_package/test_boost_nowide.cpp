// test_package/test_boost_nowide.cpp — boost1.84-nowide 1.84.0 L1 smoke test.
// Exercises Boost.Nowide the way a downstream consumer does: UTF-8 ↔ wide
// conversion (header-only API), nowide::fstream file I/O, nowide::cin/cout
// streams (compiled libboost_nowide), and nowide::system() narrow invocation.
#include <boost/nowide/convert.hpp>
#include <boost/nowide/cstdio.hpp>
#include <boost/nowide/cstdlib.hpp>
#include <boost/nowide/fstream.hpp>
#include <boost/nowide/iostream.hpp>

#include <cstdio>
#include <iostream>
#include <string>

int main() {
    // 1) widen/narrow conversion (core nowide API)
    const std::wstring wide = boost::nowide::widen("Grüße aus OHOS");
    const std::string narrow = boost::nowide::narrow(wide);
    if (narrow != "Grüße aus OHOS") {
        std::cerr << "convert round-trip mismatch: " << narrow << std::endl;
        return 1;
    }
    std::cout << "convert: widen/narrow round-trip OK (" << narrow << ")" << std::endl;

    // 2) nowide::fstream — the compiled part (filebuf.cpp/iostream.cpp)
    const std::string path = "nowide_smoke_test.txt";
    {
        boost::nowide::ofstream out(path);
        if (!out) { std::cerr << "ofstream failed to open" << std::endl; return 1; }
        out << "hello nowide on OHOS" << std::endl;
    }
    {
        boost::nowide::ifstream in(path);
        if (!in) { std::cerr << "ifstream failed to open" << std::endl; return 1; }
        std::string line;
        std::getline(in, line);
        if (line != "hello nowide on OHOS") {
            std::cerr << "fstream round-trip mismatch: " << line << std::endl;
            return 1;
        }
    }
    std::cout << "fstream: write/read round-trip OK" << std::endl;

    // 3) nowide::cin/cout/cerr global streams (iostream.cpp defines them)
    boost::nowide::cout << "iostream: nowide::cout works" << std::endl;

    // 4) nowide::remove (cstdio.cpp wraps std::remove)
    if (std::remove(path.c_str()) != 0) {
        std::cerr << "failed to clean up test file" << std::endl;
        return 1;
    }
    std::cout << "boost1.84-nowide 1.84.0: convert + fstream + iostream OK" << std::endl;
    return 0;
}
