/* compat/ut_string_class.h — OHOS minimal AbiWord ut_string_class.h shim
 *
 * Provides the UT_String 8-bit string class + UT_String_sprintf helpers
 * used by the t602 importer (UT_String members, UT_String_sprintf,
 * c_str(), operator[]).  Backed by std::string; self-contained.
 * Do not install; compile-time shim only.
 */
#ifndef UT_STRING_CLASS_H
#define UT_STRING_CLASS_H

#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include "ut_types.h"

class UT_String
{
public:
	UT_String () : m_s () {}
	UT_String (const char * sz, size_t n = 0) {
		if (n) m_s.assign (sz, n);
		else   m_s = sz ? sz : "";
	}
	UT_String (const UT_String & rhs) : m_s (rhs.m_s) {}
	UT_String (const std::string & s) : m_s (s) {}
	~UT_String () {}

	size_t size () const { return m_s.size (); }
	size_t length () const { return m_s.size (); }
	bool empty () const { return m_s.empty (); }
	void clear () { m_s.clear (); }
	void reserve (size_t n) { m_s.reserve (n); }

	UT_String substr (size_t iStart, size_t nChars) const {
		std::string sub = m_s.substr (iStart, nChars);
		return UT_String (sub.c_str (), sub.size ());
	}

	UT_String & operator= (const UT_String & rhs) { m_s = rhs.m_s; return *this; }
	UT_String & operator= (const char * rhs)      { m_s = rhs ? rhs : ""; return *this; }
	UT_String & operator= (const std::string & rhs) { m_s = rhs; return *this; }
	UT_String & operator+= (const UT_String & rhs) { m_s += rhs.m_s; return *this; }
	UT_String & operator+= (const char * rhs)      { if (rhs) m_s += rhs; return *this; }
	UT_String & operator+= (char rhs)              { m_s += rhs; return *this; }

	char   operator[] (size_t iPos) const { return m_s[iPos]; }
	char & operator[] (size_t iPos)       { return m_s[iPos]; }

	void swap (UT_String & rhs) { m_s.swap (rhs.m_s); }

	const char * c_str () const { return m_s.c_str (); }

private:
	std::string m_s;
};

inline bool operator== (const UT_String & s1, const UT_String & s2) { return strcmp (s1.c_str (), s2.c_str ()) == 0; }
inline bool operator== (const UT_String & s1, const char * s2)      { return strcmp (s1.c_str (), s2 ? s2 : "") == 0; }
inline bool operator== (const char * s1, const UT_String & s2)      { return strcmp (s1 ? s1 : "", s2.c_str ()) == 0; }
inline bool operator!= (const UT_String & s1, const UT_String & s2) { return !(s1 == s2); }
inline bool operator!= (const UT_String & s1, const char * s2)      { return !(s1 == s2); }
inline bool operator!= (const char * s1, const UT_String & s2)      { return !(s1 == s2); }
inline bool operator<  (const UT_String & s1, const UT_String & s2) { return strcmp (s1.c_str (), s2.c_str ()) < 0; }
inline UT_String operator+ (const UT_String & s1, const UT_String & s2) { UT_String r (s1); r += s2; return r; }

/* printf-style helpers (declared; defined in abiword_shim.cpp) */
UT_String & UT_String_sprintf (UT_String & inStr, const char * inFormat, ...);
UT_String   UT_String_sprintf (const char * inFormat, ...);

#endif /* UT_STRING_CLASS_H */
