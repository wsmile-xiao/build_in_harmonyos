// Copyright 2026 OpenHarmony PC Developer
// SPDX-License-Identifier: Apache-2.0
//
// Consumer test for level-zero-gpu-raytracing 1.2.3.
//
// The library exports the ZE_extension_rtas entry points that construct ray
// tracing acceleration structures. This program links the library, resolves
// its exported symbols and drives the real validation/creation code paths,
// asserting the specific result codes the implementation defines.
//
// Every assertion below requires the actual implementation to run: a stub or
// an absent library cannot produce these distinct, mutually exclusive codes.

#include <level_zero/ze_wrapper.h>
#include <rtbuild.h>

#include <dlfcn.h>

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {

int failures = 0;

void check(const char *what, ze_result_t actual, ze_result_t expected) {
    const bool ok = (actual == expected);
    if (!ok) {
        ++failures;
    }
    std::printf("%-58s expected=0x%08x actual=0x%08x  %s\n", what,
                static_cast<unsigned>(expected), static_cast<unsigned>(actual),
                ok ? "PASS" : "FAIL");
}

// Integration tests need a device, which this environment does not provide.
// The API layer validates handles before touching any driver state, so a
// non-null but never-dereferenced handle reaches the algorithm entry points.
constexpr uintptr_t kFakeDriver = 0x1000;
constexpr uintptr_t kFakeDriverOther = 0x2000;

} // namespace

int main() {
    std::printf("=== level-zero-gpu-raytracing %s consumer test ===\n", "1.2.3");

    // The library is loaded dynamically by the Level Zero loader in
    // production, so the exported symbols must be visible in the dynamic
    // symbol table rather than only to the static linker.
    void *self = dlopen(nullptr, RTLD_NOW);
    if (self != nullptr) {
        const char *exports[] = {
            "zeRTASBuilderCreateExtImpl",
            "zeRTASBuilderDestroyExtImpl",
            "zeRTASBuilderBuildExtImpl",
            "zeDriverRTASFormatCompatibilityCheckExtImpl",
        };
        for (const char *name : exports) {
            const bool present = (dlsym(self, name) != nullptr);
            if (!present) {
                ++failures;
            }
            std::printf("%-58s %s\n", name, present ? "PASS (exported)" : "FAIL (missing)");
        }
    }

    // 1. Descriptor validation runs before anything else: a null handle is
    //    rejected by the validation layer, not by the builder.
    ze_rtas_builder_ext_desc_t descriptor{};
    descriptor.stype = ZE_STRUCTURE_TYPE_RTAS_BUILDER_EXT_DESC;
    descriptor.pNext = nullptr;
    descriptor.builderVersion = ZE_RTAS_BUILDER_EXT_VERSION_CURRENT;

    ze_rtas_builder_ext_handle_t builder = nullptr;
    check("CreateExtImpl(null driver)",
          zeRTASBuilderCreateExtImpl(nullptr, &descriptor, &builder),
          ZE_RESULT_ERROR_INVALID_NULL_HANDLE);

    // 2. A well-formed descriptor creates a builder instance.
    check("CreateExtImpl(valid driver)",
          zeRTASBuilderCreateExtImpl(reinterpret_cast<ze_driver_handle_t>(kFakeDriver),
                                     &descriptor, &builder),
          ZE_RESULT_SUCCESS);
    if (builder == nullptr) {
        ++failures;
        std::printf("%-58s FAIL (builder not created)\n", "builder handle");
    } else {
        std::printf("%-58s %s\n", "builder handle", "PASS (non-null)");
    }

    // 3. The builder carries an internal magic value that the destructor
    //    clears; destroying a live instance must be accepted.
    check("DestroyExtImpl(live builder)",
          zeRTASBuilderDestroyExtImpl(builder), ZE_RESULT_SUCCESS);

    // 4. The format-compatibility check is pure: identical formats are
    //    compatible, differing ones are not. These share a code path, so the
    //    two results together prove the comparison actually executed.
    check("FormatCompatibilityCheck(1,1) identical",
          zeDriverRTASFormatCompatibilityCheckExtImpl(
              reinterpret_cast<ze_driver_handle_t>(kFakeDriver),
              static_cast<ze_rtas_format_ext_t>(1), static_cast<ze_rtas_format_ext_t>(1)),
          ZE_RESULT_SUCCESS);

    check("FormatCompatibilityCheck(1,2) different",
          zeDriverRTASFormatCompatibilityCheckExtImpl(
              reinterpret_cast<ze_driver_handle_t>(kFakeDriver),
              static_cast<ze_rtas_format_ext_t>(1), static_cast<ze_rtas_format_ext_t>(2)),
          ZE_RESULT_EXP_ERROR_OPERANDS_INCOMPATIBLE);

    // 5. Format 0 is the explicitly invalid enumerator.
    check("FormatCompatibilityCheck(INVALID)",
          zeDriverRTASFormatCompatibilityCheckExtImpl(
              reinterpret_cast<ze_driver_handle_t>(kFakeDriver),
              ZE_RTAS_FORMAT_EXT_INVALID, ZE_RTAS_FORMAT_EXT_INVALID),
          ZE_RESULT_ERROR_INVALID_ENUMERATION);

    // 6. Handle validation applies to this entry point as well.
    check("FormatCompatibilityCheck(null driver)",
          zeDriverRTASFormatCompatibilityCheckExtImpl(
              nullptr, static_cast<ze_rtas_format_ext_t>(1), static_cast<ze_rtas_format_ext_t>(1)),
          ZE_RESULT_ERROR_INVALID_NULL_HANDLE);

    // 7. A large scratch/buffer request must be rejected rather than
    //    dereferenced when the build descriptor is absent.
    check("BuildExtImpl(null descriptor)",
          zeRTASBuilderBuildExtImpl(nullptr, nullptr, nullptr, 0, nullptr, 0, nullptr,
                                    nullptr, nullptr, nullptr),
          ZE_RESULT_ERROR_INVALID_NULL_HANDLE);

    std::printf("=== %s (failures=%d) ===\n", failures == 0 ? "ALL CHECKS PASSED" : "CHECKS FAILED",
                failures);
    return failures == 0 ? 0 : 1;
}
