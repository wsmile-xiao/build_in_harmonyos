/* compat/ut_locale.h — OHOS minimal UT_LocaleTransactor shim
 * Switches the C locale for a scope; restores on destruction.
 */
#ifndef COMPAT_UT_LOCALE_H
#define COMPAT_UT_LOCALE_H

#include <locale.h>
#include <stdlib.h>
#include <string>

class UT_LocaleTransactor
{
public:
	UT_LocaleTransactor (int category, const char * locale)
		: mCategory (category)
	{
		mOldLocale = strdup (setlocale (category, 0));
		if (locale)
			setlocale (category, locale);
	}
	~UT_LocaleTransactor ()
	{
		if (mOldLocale)
		{
			setlocale (mCategory, mOldLocale);
			free (mOldLocale);
		}
	}

private:
	UT_LocaleTransactor ();
	UT_LocaleTransactor (const UT_LocaleTransactor & rhs);
	UT_LocaleTransactor & operator= (const UT_LocaleTransactor & rhs);
	int mCategory;
	char * mOldLocale;
};

#endif /* COMPAT_UT_LOCALE_H */
