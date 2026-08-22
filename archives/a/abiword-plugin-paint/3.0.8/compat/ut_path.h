/* compat/ut_path.h — OHOS minimal AbiWord ut_path.h shim
 * The AbiPaint plugin uses UT_basename() and UT_isRegularFile().
 */
#ifndef UT_PATH_H
#define UT_PATH_H

#include <string>
#include "ut_types.h"

const char * UT_basename (const char * path);
bool         UT_isRegularFile (const char * filename);
bool         UT_directoryExists (const char * dir);

#endif /* UT_PATH_H */
