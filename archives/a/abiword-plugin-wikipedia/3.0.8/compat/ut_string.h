/* compat/ut_string.h — OHOS minimal AbiWord ut_string.h shim
 * Declares the subset of src/af/util/xp/ut_string.h used by the
 * wikipedia plugin: the UCS-4 length helper.
 */
#ifndef UT_STRING_H
#define UT_STRING_H

#include "ut_types.h"

UT_uint32 UT_UCS4_strlen (const UT_UCS4Char * string);

#endif /* UT_STRING_H */
