#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "TextParser.h"
#include "tpVersion.h"

namespace fs = std::filesystem;

static int g_checks = 0;
static int g_passed = 0;

static void check(bool cond, const char* name) {
    ++g_checks;
    if (cond) {
        ++g_passed;
        std::cout << "PASS: " << name << std::endl;
    } else {
        std::cout << "FAIL: " << name << std::endl;
    }
}

int main() {
    // 1. Singleton instance must be obtainable (real API call).
    TextParser* tp = TextParser::get_instance_singleton();
    check(tp != nullptr, "get_instance_singleton returns non-null");
    if (tp == nullptr) {
        std::cout << "RESULT: " << g_passed << "/" << g_checks << std::endl;
        return 1;
    }

    // 2. Version macro must match the packaged version (real header value).
    check(std::string(TP_VERSION) == "1.9.0", "TP_VERSION is 1.9.0");

    // Fixture lives under TMPDIR because OHOS /tmp is read-only.
    // getLabels() only returns the CURRENT node's direct leaves, so at the
    // root "/" (which holds node "Demo", no direct leaves) it is empty by
    // design; the absolute-label API getAllLabels() is the correct root
    // enumeration (cf. upstream Example3_cpp). The current-node API is
    // covered after changeNode("/Demo") (cf. Example4_cpp).
    fs::path workdir;
    try {
        workdir = fs::temp_directory_path() / "textparser_test_pkg";
        fs::create_directories(workdir);
    } catch (const std::exception& e) {
        std::cout << "FAIL: create workdir: " << e.what() << std::endl;
        return 1;
    }
    std::cout << "workdir: " << workdir.string() << std::endl;
    const fs::path input = workdir / "case.tpp";
    {
        std::ofstream out(input);
        out << "\"Demo\" {\n"
            << "    \"answer\" = 42\n"
            << "    \"greeting\" = \"hello\"\n"
            << "}\n";
    }

    // 3. read fixture.
    check(tp->read(input.string()) == TP_NO_ERROR, "read fixture file");

    // 4. Absolute enumeration at root: exactly the 2 leaves under /Demo.
    std::vector<std::string> all;
    int aerr = tp->getAllLabels(all);
    std::cout << "allLabels: " << all.size() << " aerr=" << aerr << std::endl;
    for (size_t i = 0; i < all.size(); ++i) {
        std::cout << "all[" << i << "]=" << all[i] << std::endl;
    }
    check(aerr == TP_NO_ERROR && all.size() == 2, "getAllLabels finds 2 leaves");

    // 5. Absolute getValue: /Demo/answer must read back exactly "42".
    std::string aval;
    int verr = tp->getValue("/Demo/answer", aval);
    std::cout << "getValue /Demo/answer verr=" << verr << " value=[" << aval << "]" << std::endl;
    check(verr == TP_NO_ERROR && aval == "42", "getValue /Demo/answer is 42");

    // 6. Current-node API after changeNode (upstream Example4 pattern).
    std::vector<std::string> cur;
    int cerr = tp->changeNode("/Demo");
    int lerr = (cerr == TP_NO_ERROR) ? tp->getLabels(cur, 2) : cerr;
    std::cout << "changeNode cerr=" << cerr << " labels=" << cur.size() << " lerr=" << lerr << std::endl;
    for (size_t i = 0; i < cur.size(); ++i) {
        std::cout << "cur[" << i << "]=" << cur[i] << std::endl;
    }
    check(cerr == TP_NO_ERROR && lerr == TP_NO_ERROR && cur.size() == 2, "changeNode+getLabels finds 2 leaves");

    // 7. write roundtrip: file must exist and be non-empty (anti-false-pass).
    const fs::path output = workdir / "case_out.tpp";
    int werr = tp->write(output.string(), 1);
    bool wok = (werr == TP_NO_ERROR);
    std::error_code ec;
    auto sz = fs::file_size(output, ec);
    std::cout << "write werr=" << werr << " size=" << (ec ? -1 : (long long)sz) << std::endl;
    check(wok && !ec && sz > 0, "write roundtrip file non-empty");

    // 8. remove clears database.
    int rerr = tp->remove();
    std::cout << "remove rerr=" << rerr << std::endl;
    check(rerr == TP_NO_ERROR, "remove clears database");

    std::cout << "RESULT: " << g_passed << "/" << g_checks << std::endl;
    if (g_passed != 8 || g_checks != 8) {
        return 1;
    }
    std::cout << "TextParser test_package PASSED" << std::endl;
    return 0;
}
