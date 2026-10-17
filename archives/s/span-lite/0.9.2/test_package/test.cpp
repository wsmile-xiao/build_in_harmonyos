#include <nonstd/span.hpp>
#include <cstdio>
static int g_checks = 0, g_failed = 0;
#define CHECK(c) do { ++g_checks; if (!(c)) { ++g_failed; printf("FAIL: %s\n", #c); } } while(0)
int main() {
    int arr[] = {1,2,3,4,5};
    nonstd::span<int> s(arr, 5);
    CHECK(s.size() == 5);
    CHECK(s[0] == 1);
    CHECK(s.back() == 5);
    auto sub = s.subspan(1, 3);
    CHECK(sub.size() == 3);
    CHECK(sub[0] == 2);
    printf("span-lite test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed ? 1 : 0;
}
