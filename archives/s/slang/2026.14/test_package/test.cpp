// test.cpp — Slang library API test (R34: must depend on tested package)
// Tests the slang compiler API by creating a global session and checking the build tag
#include <slang.h>
#include <cstdio>

int main() {
    // Test 1: Get the build tag string (simple C API call)
    const char* buildTag = spGetBuildTagString();
    if (buildTag == nullptr || buildTag[0] == '\0') {
        fprintf(stderr, "FAIL: spGetBuildTagString returned null/empty\n");
        return 1;
    }
    printf("PASS: Slang build tag = %s\n", buildTag);

    // Test 2: Create a global session (core API)
    slang::IGlobalSession* globalSession = nullptr;
    SlangResult result = slang::createGlobalSession(&globalSession);
    if (result != SLANG_OK || globalSession == nullptr) {
        fprintf(stderr, "FAIL: createGlobalSession returned %d\n", (int)result);
        return 1;
    }
    printf("PASS: createGlobalSession succeeded\n");

    // Test 3: Get the slang version from the session
    slang::SessionDesc sessionDesc = {};
    slang::ISession* session = nullptr;
    result = globalSession->createSession(sessionDesc, &session);
    if (result != SLANG_OK || session == nullptr) {
        fprintf(stderr, "FAIL: createSession returned %d\n", (int)result);
        return 1;
    }
    printf("PASS: createSession succeeded\n");

    // Cleanup
    session->release();
    globalSession->release();

    printf("All slang API tests passed\n");
    return 0;
}
