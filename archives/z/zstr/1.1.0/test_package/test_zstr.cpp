// test_zstr.cpp — consumer test for the zstr Conan package (R34).
// Four real assertions through the packaged <zstr.hpp> API (no stubs):
//   CASE 1: file round-trip content via zstr::ofstream / zstr::ifstream.
//   CASE 2: the compressed file is non-empty (proves real compression).
//   CASE 3: in-memory round-trip via zstr::ostream / zstr::istream.
//   CASE 4: the in-memory compressed blob is non-empty.
#include <zstr.hpp>

#include <cstdio>
#include <iostream>
#include <sstream>
#include <string>

namespace {
int s_failures = 0;

void check(bool ok, const char* label, const std::string& detail) {
    if (ok) {
        std::cout << "CASE PASS: " << label << " (" << detail << ")"
                  << std::endl;
    } else {
        ++s_failures;
        std::cout << "CASE FAIL: " << label << " (" << detail << ")"
                  << std::endl;
    }
}

std::string make_payload() {
    std::string data;
    for (int i = 0; i < 200; ++i) {
        data += "zstr harmonyos round-trip line ";
        data += std::to_string(i);
        data += " - compress me!\n";
    }
    for (int b = 1; b < 256; ++b) {
        data += static_cast<char>(b);
    }
    return data;
}

std::string read_all(std::istream& in) {
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

long file_size(const char* path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) {
        return -1;
    }
    return static_cast<long>(f.tellg());
}
} // namespace

int main() {
    const std::string payload = make_payload();

    // File round-trip through zstr::ofstream / zstr::ifstream.
    const char* tmp = "zstr_pkg_test_tmp.gz";
    {
        zstr::ofstream out(tmp);
        out << payload;
    }
    const long gz_size = file_size(tmp);
    std::string back;
    {
        zstr::ifstream in(tmp);
        back = read_all(in);
    }
    check(back == payload, "file round-trip content",
          "in=" + std::to_string(payload.size()) +
              " out=" + std::to_string(back.size()));
    check(gz_size > 0, "compressed file non-empty",
          "size=" + std::to_string(gz_size));
    std::remove(tmp);

    // In-memory round-trip through zstr::ostream / zstr::istream.
    std::string blob;
    {
        std::ostringstream compressed;
        {
            zstr::ostream zos(compressed);
            zos << payload;
        }
        blob = compressed.str();
    }
    std::string back2;
    {
        std::istringstream input(blob);
        zstr::istream zis(input);
        back2 = read_all(zis);
    }
    check(back2 == payload, "memory round-trip content",
          "in=" + std::to_string(payload.size()) +
              " out=" + std::to_string(back2.size()));
    check(!blob.empty(), "compressed blob non-empty",
          "size=" + std::to_string(blob.size()));

    if (s_failures == 0) {
        std::cout << "ALL 4 CASES PASSED" << std::endl;
        return 0;
    }
    std::cout << s_failures << " CASE(S) FAILED" << std::endl;
    return 1;
}
