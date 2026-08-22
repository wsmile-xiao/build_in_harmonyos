/* compat/xap_Prefs.h — OHOS minimal AbiWord xap_Prefs.h shim
 *
 * XAP_Prefs / XAP_PrefsScheme with a value registry so the plugin's
 * preference handling works end-to-end in tests.
 */
#ifndef XAP_PREFS_H
#define XAP_PREFS_H

#include <map>
#include <string>
#include "ut_types.h"
#include "ut_vector.h"

class XAP_Prefs;

class XAP_PrefsScheme
{
public:
	XAP_PrefsScheme (XAP_Prefs * pPrefs, const gchar * szSchemeName);
	~XAP_PrefsScheme ();

	bool setValue (const gchar * szKey, const gchar * szValue);
	bool setValueBool (const gchar * szKey, bool bValue);
	bool getValue (const gchar * szKey, const gchar ** pszValue) const;
	bool getValue (const char * szKey, std::string & szValue) const;
	bool getValueBool (const gchar * szKey, bool * pbValue) const;

	const gchar * getSchemeName () const;
	bool          _test_has (const gchar * szKey) const;

private:
	std::string  m_szName;
	std::map<std::string, std::string> m_hash;
};

class XAP_Prefs
{
public:
	XAP_Prefs ();
	virtual ~XAP_Prefs ();

	XAP_PrefsScheme * getPluginScheme (const gchar * szSchemeName) const;
	bool              addPluginScheme (XAP_PrefsScheme * pNewScheme);
	UT_uint32         getPluginSchemeCount () const;

private:
	UT_GenericVector<XAP_PrefsScheme *> m_vecPluginSchemes;
};

#endif /* XAP_PREFS_H */
