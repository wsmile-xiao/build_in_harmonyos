#include <stddef.h>
#include <stdio.h>
#include <Lerc_c_api.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libLerc.so.4 exported C API (Lerc_c_api.h), 12 linkable symbols.
 * Lerc_types.h is a C++-only header (namespace/enum class), so the C surface
 * is exactly these functions plus the version macros and lerc_status. */
DECLARE_SYMBOL(lerc_computeCompressedSize);
DECLARE_SYMBOL(lerc_encode);
DECLARE_SYMBOL(lerc_computeCompressedSizeForVersion);
DECLARE_SYMBOL(lerc_encodeForVersion);
DECLARE_SYMBOL(lerc_getBlobInfo);
DECLARE_SYMBOL(lerc_getDataRanges);
DECLARE_SYMBOL(lerc_decode);
DECLARE_SYMBOL(lerc_decodeToDouble);
DECLARE_SYMBOL(lerc_computeCompressedSize_4D);
DECLARE_SYMBOL(lerc_encode_4D);
DECLARE_SYMBOL(lerc_decode_4D);
DECLARE_SYMBOL(lerc_decodeToDouble_4D);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libLerc.so.4 fails at link or load time,
     * not silently at runtime. */
    (void)probe_lerc_computeCompressedSize;
    (void)probe_lerc_encode;
    (void)probe_lerc_computeCompressedSizeForVersion;
    (void)probe_lerc_encodeForVersion;
    (void)probe_lerc_getBlobInfo;
    (void)probe_lerc_getDataRanges;
    (void)probe_lerc_decode;
    (void)probe_lerc_decodeToDouble;
    (void)probe_lerc_computeCompressedSize_4D;
    (void)probe_lerc_encode_4D;
    (void)probe_lerc_decode_4D;
    (void)probe_lerc_decodeToDouble_4D;
    return 0;
}
