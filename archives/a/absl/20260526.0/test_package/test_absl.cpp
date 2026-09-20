// absl consumer test (L0c + R34): standalone test source executed
// via self.run (clang++ link) from conanfile.py test().
// R34: actually call the tested API — absl::StrCat (header-only) +
// absl::SimpleAtoi (absl_strings lib — link check).
#include <absl/strings/numbers.h>
#include <absl/strings/str_cat.h>
#include <cstdio>
#include <string>

int main() {
    std::string s = absl::StrCat("absl-", 20260526, "-ok");
    if (s != "absl-20260526-ok") {
        std::fprintf(stderr, "StrCat mismatch: %s\n", s.c_str());
        return 1;
    }
    int v = 0;
    if (!absl::SimpleAtoi("42", &v) || v != 42) {
        std::fprintf(stderr, "SimpleAtoi failed\n");
        return 1;
    }
    std::printf("OK: absl 20260526.0 (StrCat=%s SimpleAtoi=%d)\n",
                s.c_str(), v);
    return 0;
}
