/* compat/ut_types.h — OHOS minimal AbiWord ut_types.h shim
 * Mirrors the type/macro surface of src/af/util/xp/ut_types.h used by the
 * clarisworks plugin.  Do not install; compile-time shim only.
 */
#ifndef UT_TYPES_H
#define UT_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include "glib.h"

typedef guint8            UT_Byte;
typedef gunichar          UT_UCS4Char;
typedef guint16           UT_UCS2Char;
typedef gint32            UT_GrowBufElement;
typedef UT_UCS4Char       UT_UCSChar;       /* Unicode */
typedef guint8            UT_uint8;
typedef gint8             UT_sint8;
typedef guint16           UT_uint16;
typedef gint16            UT_sint16;
typedef guint32           UT_uint32;
typedef gint32            UT_sint32;
typedef guint64           UT_uint64;
typedef gint64            UT_sint64;

/* Confidence heuristic: [0,255] */
typedef UT_uint8 UT_Confidence_t;
#define UT_CONFIDENCE_PERFECT 255
#define UT_CONFIDENCE_GOOD    170
#define UT_CONFIDENCE_SOSO    127
#define UT_CONFIDENCE_POOR     85
#define UT_CONFIDENCE_ZILCH     0

/* export / far-call macros */
#define ABI_EXPORT
#define ABI_PLUGIN_EXPORT
#define ABI_FAR_CALL extern "C" ABI_PLUGIN_EXPORT

/* error codes */
typedef UT_sint32 UT_Error;
#define UT_OK               ((UT_Error) 0)
#define UT_ERROR            ((UT_Error) -1)
#define UT_IE_FILENOTFOUND  ((UT_Error) -301)
#define UT_IE_NOMEMORY      ((UT_Error) -302)
#define UT_IE_UNKNOWNTYPE   ((UT_Error) -303)
#define UT_IE_BOGUSDOCUMENT ((UT_Error) -304)
#define UT_IE_COULDNOTOPEN  ((UT_Error) -305)
#define UT_IE_IMPORTERROR   ((UT_Error) -300)
#define UT_IE_TRY_RECOVER   ((UT_Error) -350)
#define UT_IS_IE_SUCCESS(x) (((x) == UT_OK) || ((x) == UT_IE_TRY_RECOVER))

/* AbiWord build version reported by plugins (normally from config.h) */
#define ABI_BUILD_VERSION "3.0.8"

#define UT_UNUSED(x) (void)(x);
#define UT_DEBUG_ONLY_ARG(x) (void)(x);

#define UCS_SPACE  ((UT_UCSChar)0x0020)
#define UCS_CR     ((UT_UCSChar)0x000d)
#define UCS_LF     ((UT_UCSChar)0x000a)

#define FREEP(p)    do { if (p) { free((void *)(p)); (p) = 0; } } while (0)

#endif /* UT_TYPES_H */
