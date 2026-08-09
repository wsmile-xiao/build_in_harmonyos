/* compat/ut_debugmsg.h — OHOS minimal AbiWord ut_debugmsg.h shim */
#ifndef UT_DEBUGMSG_H
#define UT_DEBUGMSG_H

#include <stdio.h>
#include "ut_types.h"

void _UT_OutputMessage (const char *s, ...);

#ifdef DEBUG
#define UT_DEBUGMSG(M) _UT_OutputMessage M
#else
#define UT_DEBUGMSG(M)
#endif

#define _UT_WarningMessage _UT_OutputMessage
#define UT_WARNINGMSG(M) _UT_WarningMessage M

#endif /* UT_DEBUGMSG_H */
