/* compat/ut_types.h — OHOS minimal AbiWord ut_types.h shim
 * Mirrors the type/macro surface of src/af/util/xp/ut_types.h used by the
 * wikipedia plugin.  Do not install; compile-time shim only.
 */
#ifndef UT_TYPES_H
#define UT_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

typedef uint8_t            UT_Byte;
typedef uint32_t           UT_UCS4Char;
typedef uint16_t           UT_UCS2Char;
typedef UT_UCS4Char        UT_UCSChar;       /* Unicode */
typedef uint8_t            UT_uint8;
typedef int8_t             UT_sint8;
typedef uint16_t           UT_uint16;
typedef int16_t            UT_sint16;
typedef uint32_t           UT_uint32;
typedef int32_t            UT_sint32;
typedef uint64_t           UT_uint64;
typedef int64_t            UT_sint64;

/* export / far-call macros (non-Windows: empty) */
#define ABI_EXPORT
#define ABI_PLUGIN_EXPORT
#define ABI_FAR_CALL extern "C" ABI_PLUGIN_EXPORT

/* AbiWord build version reported by plugins (normally from config.h) */
#define ABI_BUILD_VERSION "3.0.8"

#define UT_UNUSED(x) (void)(x);
#define UT_DEBUG_ONLY_ARG(x) (void)(x);

#define UCS_SPACE  ((UT_UCSChar)0x0020)
#define UCS_CR     ((UT_UCSChar)0x000d)
#define UCS_LF     ((UT_UCSChar)0x000a)

#define DELETEP(p)      do { if (p) { delete(p); (p)=NULL; } } while (0)
#define DELETEPV(pa)    do { if (pa) { delete [] (pa); (pa)=NULL; } } while (0)
#define FREEP(p)        do { if (p) { free((void *)(p)); (p)=NULL; } } while (0)

#endif /* UT_TYPES_H */
