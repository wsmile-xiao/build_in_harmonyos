/* compat/ut_mbtowc.h — OHOS minimal AbiWord ut_mbtowc.h shim
 *
 * UT_UCS4_mbtowc converts one multibyte character to UCS-4.  PalmDoc
 * data is US-ASCII/Latin-1, so the shim maps each byte 1:1 (low byte)
 * and always reports success — matching the importer's default path.
 */
#ifndef UT_MBTOWC_H
#define UT_MBTOWC_H

#include "ut_types.h"

class UT_UCS4_mbtowc
{
public:
	UT_UCS4_mbtowc () {}
	~UT_UCS4_mbtowc () {}

	bool mbtowc (UT_UCS4Char & wc, UT_Byte ch) const
	{
		wc = (UT_UCS4Char)(ch & 0xFF);
		return true;
	}
};

#endif /* UT_MBTOWC_H */
