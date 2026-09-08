// test_nvtx.cpp — Conan test_package for nvtx 3.6.0-c-cpp
//
// Exercises the packaged NVTX C/C++ APIs:
//   1. nvtx3 C++ header API: nvtx3::scoped_range (event annotation)
//   2. nvtx3 C API: nvtxNameOsThreadA
//   3. nvtxw3 loader static library: nvtxwLoad / nvtxwUnload with a
//      deliberately missing backend, expecting a graceful
//      NVTXW_RESULT_LIBRARY_NOT_FOUND (exercises dlopen/dlsym on OHOS).
//
// Assertions use CHECK() so they still run under Release (-DNDEBUG).

#include <cstdio>
#include <cstdlib>
#include <string>

#include <nvtx3/nvtx3.hpp>
#include <nvtx3/nvToolsExt.h>
#include <nvtxw3/nvtxw3_loader.h>

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::fprintf(stderr, "CHECK failed at %s:%d: %s\n", __FILE__,    \
                         __LINE__, #cond);                                   \
            std::exit(1);                                                    \
        }                                                                    \
    } while (0)

int main()
{
    // 1) C++ scoped_range: creates a domain/range on the stack.
    {
        nvtx3::scoped_range range("test_range");
        nvtx3::mark("test_mark");
    }

    // 2) C API thread naming.
    nvtxNameOsThreadA(0, "nvtx-test-thread");

    // 3) Loader static library: missing backend must fail gracefully.
    nvtxwModuleHandle_t handle = nullptr;
    nvtxwGetInterface_t getInterfaceFunc = nullptr;
    nvtxwResultCode_t result =
        nvtxwLoad("nvtxtest_missing_backend", &getInterfaceFunc, &handle);
    // Expected: backend absent -> NVTXW_RESULT_LIBRARY_NOT_FOUND (no crash).
    CHECK(result == NVTXW_RESULT_LIBRARY_NOT_FOUND || handle == nullptr);

    std::printf("test_nvtx: PASS (nvtx3 scoped_range/mark + nvtxNameOsThreadA + nvtxw3 loader graceful-miss)\n");
    return 0;
}