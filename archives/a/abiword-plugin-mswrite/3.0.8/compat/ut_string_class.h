/* compat/ut_string_class.h — OHOS minimal UT_String/UT_UCS4String shim
 * Subset used by the mswrite plugin: UT_String (std::string wrapper),
 * UT_String_sprintf, and UT_UCS4String (UCS-4 text buffer with
 * ucs4_str()/utf8_str()/size()/clear()/operator+=).
 */
#ifndef COMPAT_UT_STRING_CLASS_H
#define COMPAT_UT_STRING_CLASS_H

#include <stdarg.h>
#include <stdio.h>
#include <string>
#include <vector>
#include "ut_types.h"

typedef std::string UT_String;

inline UT_String & UT_String_sprintf (UT_String & inStr, const char * inFormat, ...)
{
	va_list args;
	va_start (args, inFormat);
	char buf[2048];
	int n = vsnprintf (buf, sizeof (buf), inFormat, args);
	va_end (args);
	/* vsnprintf < 0 = encoding error；>= sizeof(buf) = 截断——均不静默吞掉，
	 * 截断时至少保证缓冲区内容可识别（buf 始终 NUL 结尾）。 */
	inStr = (n < 0) ? UT_String () : UT_String (buf);
	return inStr;
}

inline UT_String UT_String_sprintf (const char * inFormat, ...)
{
	va_list args;
	va_start (args, inFormat);
	char buf[2048];
	int n = vsnprintf (buf, sizeof (buf), inFormat, args);
	va_end (args);
	if (n < 0)
		return UT_String ();
	return UT_String (buf);
}

/* UCS-4 text buffer (mswrite translate_char / mText) */
class UT_UCS4String
{
public:
	UT_UCS4String () {}
	UT_UCS4String (const UT_UCS4String & rhs) : m_buf (rhs.m_buf) {}

	UT_UCS4String & operator= (const UT_UCS4String & rhs)
	{
		if (this != &rhs)
			m_buf = rhs.m_buf;
		return *this;
	}

	UT_UCS4String & operator+= (UT_UCS4Char ch)
	{
		m_buf.push_back (ch);
		return *this;
	}

	UT_UCS4String & operator+= (const char * s)
	{
		for (const char * p = s; *p; p++)
			m_buf.push_back (static_cast<UT_UCS4Char> (static_cast<unsigned char> (*p)));
		return *this;
	}

	void clear () { m_buf.clear (); }
	size_t size () const { return m_buf.size (); }

	const UT_UCS4Char * ucs4_str () const
	{
		m_terminated.assign (m_buf.begin (), m_buf.end ());
		m_terminated.push_back (0);
		return &m_terminated[0];
	}

	/* minimal UTF-8 encoding for debug output */
	std::string utf8_str () const
	{
		std::string out;
		for (size_t i = 0; i < m_buf.size (); i++)
		{
			UT_UCS4Char ch = m_buf[i];
			if (ch < 0x80)
				out += static_cast<char> (ch);
			else if (ch < 0x800)
			{
				out += static_cast<char> (0xC0 | (ch >> 6));
				out += static_cast<char> (0x80 | (ch & 0x3F));
			}
			else if (ch < 0x10000)
			{
				out += static_cast<char> (0xE0 | (ch >> 12));
				out += static_cast<char> (0x80 | ((ch >> 6) & 0x3F));
				out += static_cast<char> (0x80 | (ch & 0x3F));
			}
			else
			{
				/* ≥ U+10000：4 字节编码（审查 P3，之前误用 3 字节） */
				out += static_cast<char> (0xF0 | (ch >> 18));
				out += static_cast<char> (0x80 | ((ch >> 12) & 0x3F));
				out += static_cast<char> (0x80 | ((ch >> 6) & 0x3F));
				out += static_cast<char> (0x80 | (ch & 0x3F));
			}
		}
		return out;
	}

private:
	std::vector<UT_UCS4Char> m_buf;
	mutable std::vector<UT_UCS4Char> m_terminated;
};

#endif /* COMPAT_UT_STRING_CLASS_H */
