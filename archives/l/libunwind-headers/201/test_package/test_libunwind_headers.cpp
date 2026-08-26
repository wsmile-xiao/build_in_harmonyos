// Consumer test for libunwind-headers 201.
//
// This exercises the real public surface of the packaged Apple libunwind
// headers: the error-code enum, the aarch64 register numbers, the public
// unw_context_t / unw_cursor_t / unw_proc_info_t types, the compact-unwind
// encoding constants from <mach-o/compact_unwind_encoding.h>, and the
// visibility of the `extern "C"` API declarations (by taking their address).
//
// It does NOT call any unwind function: those live in the libunwind runtime,
// which this headers package deliberately does not build or link.

#include <libunwind.h>
#include <mach-o/compact_unwind_encoding.h>

#include <cstdint>

int main()
{
    // 1. Error codes from <libunwind.h>.
    static_assert(UNW_ESUCCESS == 0);
    static_assert(UNW_EUNSPEC == -6540);
    static_assert(UNW_ESTOPUNWIND == -6544);
    static_assert(UNW_ENOINFO == -6549);

    // 2. AARCH64 register numbers (this package targets OHOS aarch64).
    static_assert(UNW_ARM64_X0 == 0);
    static_assert(UNW_ARM64_FP == 29);
    static_assert(UNW_ARM64_LR == 30);
    static_assert(UNW_ARM64_SP == 31);
    static_assert(UNW_ARM64_RA_SIGN_STATE == 34);

    // 3. Public types are usable.
    static_assert(sizeof(unw_word_t) == sizeof(uintptr_t));
    static_assert(sizeof(unw_context_t) > 0);
    static_assert(sizeof(unw_cursor_t) > 0);

    // 4. Compact-unwind constants from <mach-o/compact_unwind_encoding.h>.
    static_assert(UNWIND_IS_NOT_FUNCTION_START == 0x80000000);
    static_assert(UNWIND_HAS_LSDA == 0x40000000);
    static_assert(UNWIND_SECTION_VERSION == 1);

    // 5. Instantiate the public procedure-info struct and write fields.
    unw_proc_info_t info{};
    info.start_ip = 0x1000;
    info.end_ip = 0x2000;
    info.format = 0;

    // 6. A compact-unwind struct from the encoding header.
    unwind_info_section_header header{};
    header.version = UNWIND_SECTION_VERSION;
    header.commonEncodingsArrayCount = 4;
    header.indexCount = 2;

    // 7. The `extern "C"` API declarations are visible (address, not call).
    auto getcontext_ptr = &unw_getcontext;
    auto step_ptr = &unw_step;

    if (info.start_ip != 0x1000 || info.end_ip != 0x2000 || info.format != 0) {
        return 1;
    }
    if (header.version != 1 || header.commonEncodingsArrayCount != 4 ||
        header.indexCount != 2) {
        return 2;
    }
    if (getcontext_ptr == nullptr || step_ptr == nullptr) {
        return 3;
    }
    return 0;
}
