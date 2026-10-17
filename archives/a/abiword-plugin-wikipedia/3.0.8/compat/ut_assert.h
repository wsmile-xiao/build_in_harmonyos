/* compat/ut_assert.h — OHOS minimal AbiWord ut_assert.h shim */
#ifndef UT_ASSERT_H
#define UT_ASSERT_H

#include <assert.h>

#define UT_ASSERT(x) assert(x)
#define UT_ASSERT_HARMLESS(cond) assert(cond)
#define UT_return_if_fail(cond)    do { if (!(cond)) { assert(cond); return; } } while (0)
#define UT_return_val_if_fail(cond, val) do { if (!(cond)) { assert(cond); return (val); } } while (0)

#define UT_NOT_IMPLEMENTED   0
#define UT_SHOULD_NOT_HAPPEN 0
#define UT_TODO              0
#define UT_NOT_REACHED       0
#define UT_ASSERT_NOT_REACHED() assert(0)

#endif /* UT_ASSERT_H */
