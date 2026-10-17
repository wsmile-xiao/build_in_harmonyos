/* compat/pd_Document.h — OHOS minimal AbiWord PD_Document stub
 *
 * Importers append into the document model via IE_Imp::appendStrux /
 * appendSpan.  This stub records the strux stream and all text spans so a
 * test can verify that a real ClarisWorks file was parsed end-to-end.
 * Do not install; compile-time shim only.
 */
#ifndef PD_DOCUMENT_H
#define PD_DOCUMENT_H

#include <string>
#include <vector>
#include "ut_types.h"

typedef UT_uint32 PT_DocPosition;

typedef enum _PTStruxType
{
	PTX_Section = 0,
	PTX_Block,
	PTX_SectionHdrFtr,
	PTX_SectionEndnote,
	PTX_SectionTable,
	PTX_SectionCell,
	PTX_SectionFootnote,
	PTX_SectionMarginnote,
	PTX_SectionAnnotation,
	PTX_SectionFrame,
	PTX_SectionTOC,
	PTX_Endnote,
	PTX_Annotation,
	PTX_StruxDummy
} PTStruxType;

class PD_DocumentRange;

class PD_Document
{
public:
	PD_Document ();
	~PD_Document ();

	bool appendStrux (PTStruxType type, const char ** attributes);
	bool appendSpan (const UT_UCSChar * text, UT_uint32 length);

	/* ---- test hooks (OHOS compat shim) ---- */
	const std::vector<PTStruxType> & struxList () const { return m_struxes; }
	std::string getExtractedText () const;
	UT_uint32 getStruxCount () const { return (UT_uint32)m_struxes.size(); }
	UT_uint32 getSpanCount () const { return m_spanCount; }

private:
	std::vector<PTStruxType>  m_struxes;
	std::vector<UT_UCSChar>   m_text;
	UT_uint32                 m_spanCount;
};

class PD_DocumentRange
{
public:
	PD_Document *  m_pDoc;
	PT_DocPosition m_pos1;
	PT_DocPosition m_pos2;
};

#endif /* PD_DOCUMENT_H */
