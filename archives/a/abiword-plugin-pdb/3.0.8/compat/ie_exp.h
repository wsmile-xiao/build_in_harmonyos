/* compat/ie_exp.h — OHOS minimal AbiWord exporter framework shim
 *
 * Implements the subset of src/wp/impexp/xp/ie_exp.h used by the pdb
 * plugin.  IE_Exp::registerExporter keeps a registry so a test can reach
 * the sniffer registered by the plugin module.
 */
#ifndef IE_EXP_H
#define IE_EXP_H

#include <string>
#include <vector>
#include "ut_types.h"
#include "ie_types.h"
#include "pd_Document.h"
#include "gsf/gsf-output.h"

class PD_Document;
class IE_Exp;

class IE_ExpSniffer
{
	friend class IE_Exp;

public:
	virtual ~IE_ExpSniffer ();

	inline bool supportsFileType (IEFileType type) { return m_type == type; }
	inline IEFileType getFileType () const { return m_type; }

	virtual bool recognizeSuffix (const char * szSuffix) = 0;
	virtual bool getDlgLabels (const char ** szDesc, const char ** szSuffixList,
	                           IEFileType * ft) = 0;
	virtual UT_Error constructExporter (PD_Document * pDocument, IE_Exp ** ppie) = 0;

	const std::string & name () const { return m_name; }

protected:
	IE_ExpSniffer (const char * name);

	inline void setFileType (IEFileType type) { m_type = type; }

private:
	const std::string m_name;
	IEFileType        m_type;
};

class IE_Exp
{
public:
	virtual ~IE_Exp ();

	static void registerExporter (IE_ExpSniffer * sniffer);
	static void unregisterExporter (IE_ExpSniffer * sniffer);
	static std::vector<IE_ExpSniffer *> & registeredExporters ();   /* test hook */

	UT_Error writeDocument ();            /* public entry -> _writeDocument() */
	PD_Document * getDoc () const { return m_pDocument; }

	GsfOutput *  getFp () const { return m_fp; }
	const char * getFileName () const { return m_fileName.c_str (); }

	/* OHOS compat test hook: attach the output stream + file name */
	void setOutput (GsfOutput * fp, const char * fileName);

protected:
	IE_Exp (PD_Document * pDocument);

	virtual UT_Error _writeDocument () = 0;

private:
	PD_Document * m_pDocument;
	GsfOutput *   m_fp;
	std::string   m_fileName;
};

#endif /* IE_EXP_H */
