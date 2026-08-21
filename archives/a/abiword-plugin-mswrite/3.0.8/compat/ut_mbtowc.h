/* compat/ut_mbtowc.h — OHOS minimal multibyte-to-widechar shim
 * Subset used by the mswrite plugin: UT_UCS2_mbtowc / UT_UCS4_mbtowc
 * (single-byte charset → UCS-2/UCS-4 conversion; CP1252 only).
 */
#ifndef COMPAT_UT_MBTOWC_H
#define COMPAT_UT_MBTOWC_H

#include "ut_types.h"

/* CP1252 high-half mapping (byte 0x80..0x9F → Unicode) */
static const UT_UCS2Char cp1252_high[32] = {
	0x20AC, 0x0081, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021,
	0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0x008D, 0x017D, 0x008F,
	0x0090, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014,
	0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x009D, 0x017E, 0x0178
};

class UT_UCS2_mbtowc
{
public:
	UT_UCS2_mbtowc (const char * from_charset)
		: m_charset (from_charset ? from_charset : "CP1252") {}
	~UT_UCS2_mbtowc () {}

	void setInCharset (const char * charset)
	{
		if (charset)
			m_charset = charset;
	}

	int mbtowc (UT_UCS2Char & wc, char mb)
	{
		unsigned char b = static_cast<unsigned char> (mb);
		if (b < 0x80)
		{
			wc = b;
			return 1;
		}
		if (b >= 0x80 && b <= 0x9F)
			wc = cp1252_high[b - 0x80];
		else
			wc = b;  /* Latin-1 high half passthrough */
		return 1;
	}

private:
	UT_UCS2_mbtowc ();
	UT_UCS2_mbtowc (const UT_UCS2_mbtowc & v);
	UT_UCS2_mbtowc & operator= (const UT_UCS2_mbtowc & rhs);
	std::string m_charset;
};

class UT_UCS4_mbtowc
{
public:
	UT_UCS4_mbtowc (const char * from_charset = 0)
		: m_charset (from_charset ? from_charset : "CP1252") {}
	~UT_UCS4_mbtowc () {}

	void setInCharset (const char * charset)
	{
		if (charset)
			m_charset = charset;
	}

	int mbtowc (UT_UCS4Char & wc, char mb)
	{
		unsigned char b = static_cast<unsigned char> (mb);
		if (b < 0x80)
		{
			wc = b;
			return 1;
		}
		if (b >= 0x80 && b <= 0x9F)
			wc = cp1252_high[b - 0x80];
		else
			wc = b;
		return 1;
	}

private:
	UT_UCS4_mbtowc (const UT_UCS4_mbtowc & v);
	UT_UCS4_mbtowc & operator= (const UT_UCS4_mbtowc & rhs);
	std::string m_charset;
};

#endif /* COMPAT_UT_MBTOWC_H */
