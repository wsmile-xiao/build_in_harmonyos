/* compat/ie_imp.h — OHOS minimal AbiWord importer framework shim
 *
 * Implements the subset of src/wp/impexp/xp/ie_imp.h used by the
 * clarisworks plugin.  IE_Imp::registerImporter keeps a registry so a
 * test can reach the sniffer registered by the plugin module.
 */
#ifndef IE_IMP_H
#define IE_IMP_H

#include <string>
#include <vector>
#include "ut_types.h"
#include "ie_types.h"
#include "pd_Document.h"
#include "gsf/gsf-input.h"

class PD_Document;
class IE_Imp;

class IE_ImpSniffer
{
	friend class IE_Imp;

public:
	virtual ~IE_ImpSniffer ();

	inline bool supportsFileType (IEFileType type) { return m_type == type; }
	inline IEFileType getFileType () const { return m_type; }

	virtual UT_Confidence_t recognizeContents (const char * szBuf, UT_uint32 iNumbytes);
	virtual UT_Confidence_t recognizeContents (GsfInput * input);

	virtual const IE_SuffixConfidence * getSuffixConfidence () = 0;
	virtual const IE_MimeConfidence * getMimeConfidence () = 0;
	virtual bool getDlgLabels (const char ** szDesc, const char ** szSuffixList,
	                           IEFileType * ft) = 0;
	virtual UT_Error constructImporter (PD_Document * pDocument, IE_Imp ** ppie) = 0;

	const std::string & name () const { return m_name; }

protected:
	IE_ImpSniffer (const char * name);

	inline void setFileType (IEFileType type) { m_type = type; }

private:
	const std::string m_name;
	IEFileType        m_type;
};

class IE_Imp
{
public:
	virtual ~IE_Imp ();

	static void registerImporter (IE_ImpSniffer * sniffer);
	static void unregisterImporter (IE_ImpSniffer * sniffer);
	static std::vector<IE_ImpSniffer *> & registeredImporters ();   /* test hook */

	UT_Error importFile (GsfInput * input);
	PD_Document * getDoc () const { return m_pDocument; }

protected:
	IE_Imp (PD_Document * pDocument);

	virtual bool appendStrux (PTStruxType pts, const char ** attributes);
	virtual bool appendSpan (const UT_UCSChar * p, UT_uint32 length);

	virtual UT_Error _loadFile (GsfInput * input) = 0;

private:
	PD_Document * m_pDocument;
};

#endif /* IE_IMP_H */
