/* compat/ut_string_class.h — OHOS minimal AbiWord UT_String shim
 * The wikipedia plugin only builds a UT_String from a literal and
 * concatenates ASCII chunks (url += "..." + c_str()), so a thin
 * std::string wrapper is sufficient.
 */
#ifndef UT_STRING_CLASS_H
#define UT_STRING_CLASS_H

#include <string>
#include <string.h>
#include "ut_types.h"
#include "ut_assert.h"
#include "ut_string.h"

class ABI_EXPORT UT_String
{
public:
	UT_String () : m_s () {}
	UT_String (const char * sz, size_t n = 0)
		: m_s (sz ? (n ? std::string (sz, n) : std::string (sz)) : std::string ())
	{}
	UT_String (const std::basic_string<char> & s) : m_s (s) {}

	size_t   size () const { return m_s.size (); }
	size_t   length () const { return m_s.size (); }
	bool     empty () const { return m_s.empty (); }
	const char * c_str () const { return m_s.c_str (); }

	UT_String & operator= (const char * rhs) { m_s = rhs ? rhs : ""; return *this; }
	UT_String & operator+= (const UT_String & rhs) { m_s += rhs.m_s; return *this; }
	UT_String & operator+= (const char * rhs) { if (rhs) m_s += rhs; return *this; }
	UT_String & operator+= (char rhs) { m_s += rhs; return *this; }

private:
	std::string m_s;
};

/* strcmp-style ordering used by hash containers */
inline bool operator== (const UT_String & s1, const UT_String & s2)
{ return strcmp (s1.c_str (), s2.c_str ()) == 0; }
inline bool operator== (const UT_String & s1, const char * s2)
{ return s1.c_str () == s2 || strcmp (s1.c_str (), s2) == 0; }
inline bool operator== (const char * s1, const UT_String & s2)
{ return s1 == s2.c_str () || strcmp (s1, s2.c_str ()) == 0; }

#endif /* UT_STRING_CLASS_H */
