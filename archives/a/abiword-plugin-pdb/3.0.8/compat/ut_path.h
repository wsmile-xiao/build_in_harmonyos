/* compat/ut_path.h — OHOS minimal AbiWord ut_path.h shim
 *
 * Provides UT_basename() (POSIX basename semantics) used by
 * ie_exp_PalmDoc.cpp when it stamps the PDB database name.
 */
#ifndef UT_PATH_H
#define UT_PATH_H

const char * UT_basename (const char * pPath);

#endif /* UT_PATH_H */
