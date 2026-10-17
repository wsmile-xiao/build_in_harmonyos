// L1 test for rocm-hipamd 5.7.1 (header-library package).
//
// Real-symbol coverage from the HIP headers that are self-contained in this
// package (host compile, no GPU required):
//   hip_common.h    - __HIP_ARCH_HAS_* feature macros (host build: 0)
//   library_types.h - hipDataType / hipLibraryPropertyType enums
//                     (requires __HIP_PLATFORM_AMD__, set in CMakeLists.txt)
//   hip_profile.h   - HIP_END_MARKER macro
//
// Headers such as hip_runtime_api.h, driver_types.h or surface_types.h
// transitively require hipMemoryType or amd_detail/ from the ROCm clr runtime
// repository and cannot be compiled on host without that dependency; their
// presence in the package is verified by the artifact checks in
// test_package/conanfile.py::test().

#include <cstdio>
#include <hip/hip_common.h>
#include <hip/hip_profile.h>
#include <hip/library_types.h>

static int failures = 0;

#define CHECK(cond)                              \
    do {                                         \
        if (!(cond)) {                           \
            printf("FAIL: %s\n", #cond);         \
            failures++;                          \
        }                                        \
    } while (0)

int main(void) {
    /* hip_common.h: host (non-device) builds expose feature macros as 0 */
    CHECK(__HIP_ARCH_HAS_DOUBLES__ == 0);
    CHECK(__HIP_ARCH_HAS_WARP_SHUFFLE__ == 0);
    CHECK(__HIP_ARCH_HAS_GLOBAL_INT32_ATOMICS__ == 0);

    /* library_types.h: hipDataType enum values are stable public API */
    hipDataType dtype = HIP_R_32F;
    CHECK(dtype == 0);
    CHECK(HIP_R_64F == 1);
    CHECK(HIP_C_32F == 4);
    CHECK(HIP_R_16BF == 14);
    hipLibraryPropertyType prop = HIP_LIBRARY_MAJOR_VERSION;
    CHECK(prop == 0);

    /* hip_profile.h */
    HIP_END_MARKER();

    printf("rocm-hipamd 5.7.1 header test: %s (%d failures)\n",
           failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
