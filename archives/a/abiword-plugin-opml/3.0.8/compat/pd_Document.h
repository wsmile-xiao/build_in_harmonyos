/* compat/pd_Document.h — OHOS minimal AbiWord PD_Document shim
 *
 * Importers append into the document model via IE_Imp::appendStrux /
 * appendSpan / appendObject / appendFmt.  This stub records the strux
 * stream, all text spans, objects, lists and metadata so a test can verify
 * that a real OPML document was parsed end-to-end.
 * Do not install; compile-time shim only.
 */
#ifndef PD_DOCUMENT_H
#define PD_DOCUMENT_H

#include <string>
#include <vector>
#include <utility>

#include "ut_types.h"
#include "pt_Types.h"
#include "fl_AutoNum.h"

typedef UT_uint32 PT_DocPosition;

class PD_DocumentRange;

class PD_Document
{
public:
	PD_Document ();
	~PD_Document ();

	bool appendStrux (PTStruxType type, const char ** attributes);
	bool appendSpan (const UT_UCSChar * text, UT_uint32 length);
	bool appendObject (PTObjectType type, const char ** attributes);
	bool appendFmt (const char ** attributes);
	void popInlineFmt ();
	void addList (fl_AutoNumPtr an);
	void setMetaDataProp (const char * key, const char * value);

	/* ---- test hooks (OHOS compat shim) ---- */
	const std::vector<PTStruxType> & struxList () const { return m_struxes; }
	std::string getExtractedText () const;
	UT_uint32 getStruxCount () const { return (UT_uint32)m_struxes.size(); }
	UT_uint32 getSpanCount () const { return m_spanCount; }
	UT_uint32 getObjectCount () const { return (UT_uint32)m_objects.size(); }
	UT_uint32 countObjects (PTObjectType t) const;
	UT_uint32 getListCount () const { return (UT_uint32)m_lists.size(); }
	const std::vector<std::pair<std::string,std::string> > & metadata () const
		{ return m_metadata; }
	const char * getMetaDataProp (const char * key) const;

private:
	std::vector<PTStruxType>  m_struxes;
	std::vector<UT_UCSChar>   m_text;
	UT_uint32                 m_spanCount;
	std::vector<PTObjectType> m_objects;
	UT_uint32                 m_fmtDepth;
	std::vector<fl_AutoNumPtr> m_lists;
	std::vector<std::pair<std::string,std::string> > m_metadata;
};

class PD_DocumentRange
{
public:
	PD_Document *  m_pDoc;
	PT_DocPosition m_pos1;
	PT_DocPosition m_pos2;
};

#endif /* PD_DOCUMENT_H */
