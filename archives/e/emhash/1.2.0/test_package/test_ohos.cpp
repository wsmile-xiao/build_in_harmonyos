// test_ohos.cpp — emhash 1.2.0 HarmonyOS 专项测试
// Real, executable, HarmonyOS-specific verification:
//  1. EMHASH_VERSION_STRING macro is exposed and parses as a sane version.
//     NOTE (upstream finding): tag v1.2.0's official version.hpp / VERSION
//     file still self-report "1.1.0" (upstream did not bump the in-tree
//     version when tagging v1.2.0). We assert the macro is non-empty, starts
//     with "1." and is semver-shaped, and print the actual value instead of
//     hard-coding an expected string that the upstream headers do not carry.
//  2. The emilib headers (emihmap4/emihset3) use SSE2 intrinsics that on
//     aarch64 are translated via include/sse2neon.h — this exercises the
//     SSE2->NEON translation path actually required on HarmonyOS/OHOS aarch64.
//  3. A full CRUD round-trip with observable, asserted results.
// Only public installed headers are used. Non-zero exit on any failure.
#include <cassert>
#include <cstdint>
#include <cctype>
#include <iostream>
#include <string>
#include "emhash/version.hpp"
#include "emilib/emihmap4.hpp"
#include "emilib/emihset3.hpp"

static bool semver_like(const std::string& s) {
    int dots = 0;
    for (char c : s) {
        if (c == '.') { ++dots; continue; }
        if (!std::isdigit(static_cast<unsigned char>(c))) return false;
    }
    return !s.empty() && dots >= 1;
}

int main() {
    // 1. Version macro exposed by the installed public header.
    const std::string vs = emhash::version_string;
    assert(!vs.empty() && vs.rfind("1.", 0) == 0 && semver_like(vs));
    std::cout << "emhash::version_string = " << vs << " (upstream v1.2.0 tag "
              << "self-reports this in-tree value)" << std::endl;

    // 2. emilib4 (SSE2 intrinsics -> NEON via sse2neon.h on aarch64)
    emilib4::HashMap<std::string, int> m4;
    m4["alpha"] = 1;
    m4["beta"] = 2;
    m4["gamma"] = 3;
    assert(m4.size() == 3);
    assert(m4["beta"] == 2);
    assert(m4.find("alpha") != m4.end());
    assert(m4.find("delta") == m4.end());
    m4.erase("beta");
    assert(m4.size() == 2 && !m4.contains("beta"));

    // 3. emilib3 set (also SSE2->NEON path)
    emilib3::HashSet<int> s3;
    for (int i = 0; i < 1000; ++i) s3.insert(i % 500);
    assert(s3.size() == 500);
    for (int i = 0; i < 500; ++i) assert(s3.contains(i));
    assert(!s3.contains(999));

    std::cout << "ohos: SSE2->NEON emilib4/emilib3 OK, m4.size=" << m4.size()
              << " s3.size=" << s3.size() << std::endl;
    return 0;
}
