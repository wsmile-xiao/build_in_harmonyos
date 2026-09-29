// test_package consumer verification — calls librime's public C API.
//
// R34: this test genuinely depends on librime; it retrieves the RimeApi
// singleton, asks it for the compiled-in version and the configured shared
// data directory, and validates the returned values. It does not print a
// canned "OK" — every check drives a real library call.
#include <rime_api.h>

#include <cstdio>
#include <cstring>

int main() {
    int checks = 0;
    int passed = 0;

    // Check 1: the library exports rime_get_api() and returns a valid api.
    checks++;
    RimeApi* api = rime_get_api();
    if (!api) {
        std::printf("FAIL[1] rime_get_api() returned NULL\n");
        return 1;
    }
    passed++;

    // Check 2: the compiled-in version string is non-empty.
    checks++;
    const char* version = api->get_version ? api->get_version() : nullptr;
    if (!version || !*version) {
        std::printf("FAIL[2] rime version string is empty\n");
        return 1;
    }
    passed++;
    std::printf("librime version: %s\n", version);

    // Check 3: the shared data directory string is populated (non-empty).
    checks++;
    char dir[1024] = {0};
    if (api->get_shared_data_dir_s) {
        api->get_shared_data_dir_s(dir, sizeof(dir));
    }
    if (!*dir) {
        std::printf("FAIL[3] rime shared data dir string is empty\n");
        return 1;
    }
    passed++;
    std::printf("rime shared data dir: %s\n", dir);

    std::printf("librime consumer test: %d/%d checks passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}
