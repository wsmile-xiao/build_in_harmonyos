/* compat/ut_string_class.h — OHOS minimal AbiWord ut_string_class.h shim
 *
 * Provides UT_String (std::string), UT_UTF8String, UT_UCS4String and the
 * UT_String_sprintf helpers used by the OPML importer.  Do not install;
 * compile-time shim only.
 */
#ifndef UT_STRING_CLASS_H
#define UT_STRING_CLASS_H

#include <stdarg.h>
#include <stdio.h>
#include <string>
#include <vector>

#include "ut_types.h"

typedef std::string UT_String;

/* ================================================================== */
/* UT_UTF8String — encoding is always UTF-8                           */
/* ================================================================== */

class UT_UTF8String
{
public:
	UT_UTF8String () {}
	UT_UTF8String (const char * sz) : m_str (sz ? sz : "") {}
	UT_UTF8String (const std::string & s) : m_str (s) {}

	size_t  length () const { return m_str.size (); }
	size_t  size () const { return m_str.size (); }
	bool    empty () const { return m_str.empty (); }
	const char * utf8_str () const { return m_str.c_str (); }

	UT_UTF8String & operator= (const char * rhs) { m_str = rhs ? rhs : ""; return *this; }
	UT_UTF8String & operator= (const std::string & rhs) { m_str = rhs; return *this; }

private:
	std::string m_str;
};

/* ================================================================== */
/* UT_UCS4String — array of UT_UCS4Char (Unicode code points)         */
/* ================================================================== */

class UT_UCS4String
{
public:
	UT_UCS4String () {}
	UT_UCS4String (const UT_UCS4Char * sz, size_t n = 0);
	UT_UCS4String (const char * utf8_str, size_t bytelength = 0);
	UT_UCS4String (const std::string & str);

	size_t  length () const { return m_str.size (); }
	size_t  size () const { return m_str.size (); }
	const UT_UCS4Char * ucs4_str () const { return m_str.data (); }

	UT_UCS4String & operator= (const UT_UCS4String & rhs) { m_str = rhs.m_str; return *this; }

private:
	std::vector<UT_UCS4Char> m_str;
};

/* ================================================================== */
/* UT_String_sprintf helpers — dynamic buffer, never silently truncates */
/* ================================================================== */

inline UT_String & UT_String_sprintf (UT_String & inStr, const char * inFormat, ...)
{
	va_list args;
	va_start (args, inFormat);
	va_list args2;
	va_copy (args2, args);
	int n = vsnprintf (NULL, 0, inFormat, args2);
	va_end (args2);
	if (n < 0) {
		va_end (args);
		inStr.clear ();
		return inStr;
	}
	std::vector<char> buf ((size_t)n + 1);
	vsnprintf (buf.data (), buf.size (), inFormat, args);
	va_end (args);
	inStr.assign (buf.data (), (size_t)n);
	return inStr;
}

inline UT_String UT_String_sprintf (const char * inFormat, ...)
{
	va_list args;
	va_start (args, inFormat);
	va_list args2;
	va_copy (args2, args);
	int n = vsnprintf (NULL, 0, inFormat, args2);
	va_end (args2);
	UT_String out;
	if (n < 0) {
		va_end (args);
		return out;
	}
	std::vector<char> buf ((size_t)n + 1);
	vsnprintf (buf.data (), buf.size (), inFormat, args);
	va_end (args);
	out.assign (buf.data (), (size_t)n);
	return out;
}

#endif /* UT_STRING_CLASS_H */
