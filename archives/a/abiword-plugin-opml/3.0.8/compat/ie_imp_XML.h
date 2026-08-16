/* compat/ie_imp_XML.h — OHOS minimal AbiWord IE_Imp_XML shim
 *
 * The OPML importer derives from IE_Imp_XML (AbiWord's own XML importer
 * base class, NOT libxml2) and drives the XML parser via the virtual
 * startElement / endElement / charData callbacks.  This shim provides the
 * class surface plus a self-contained SAX-style XML parser implemented in
 * abiword_shim.cpp (_parse_xml()).  Do not install; compile-time shim only.
 */
#ifndef IE_IMP_XML_H
#define IE_IMP_XML_H

#include <stdio.h>
#include <string.h>
#include <vector>

#include "ut_types.h"
#include "ut_debugmsg.h"
#include "ut_assert.h"
#include "ut_string_class.h"
#include "ie_imp.h"
#include "pd_Document.h"
#include "pt_Types.h"
#include "gsf/gsf-input.h"

struct xmlToIdMapping {
	const char * m_name;
	int          m_type;
};

class IE_Imp_XML : public IE_Imp
{
public:
	IE_Imp_XML (PD_Document * pDocument, bool whiteSignificant);
	virtual ~IE_Imp_XML ();

	/* (Partial) implementation of the XML listener interface.
	 * Derived importers must override startElement / endElement;
	 * charData has a default (empty) implementation. */
	virtual void startElement (const gchar * name, const gchar ** atts);
	virtual void endElement (const gchar * name);
	virtual void charData (const gchar * buffer, int length);

protected:
	virtual UT_Error  _loadFile (GsfInput * input);

	int              _mapNameToToken (const char * name, xmlToIdMapping * idlist, int len);
	const gchar *    _getXMLPropValue (const gchar * name, const gchar ** atts);

	void             _pushInlineFmt (const gchar ** atts);
	void             _popInlineFmt (void);

	typedef enum _parseState {
		_PS_Init,
		_PS_Doc,
		_PS_Sec,
		_PS_Block,
		_PS_DataSec,
		_PS_DataItem,
		_PS_StyleSec,
		_PS_Style,
		_PS_IgnoredWordsSec,
		_PS_IgnoredWordsItem,
		_PS_ListSec,
		_PS_List,
		_PS_Field,
		_PS_PageSize,
		_PS_MetaData,
		_PS_Meta,
		_PS_RevisionSec,
		_PS_Revision,
		_PS_AuthorSec,
		_PS_Author,
		_PS_HistorySec,
		_PS_Table,
		_PS_Cell,
		_PS_Version,
		_PS_RDFTriple,
		_PS_RDFData,
	} ParseState;

	UT_Error    m_error;
	ParseState  m_parseState;
	bool        m_bWhiteSignificant;

private:
	int m_iInlineFmtDepth;

	/* minimal SAX-style XML parser driving the listener callbacks */
	static UT_Error _parse_xml (IE_Imp_XML * listener, const char * data, size_t len);
};

#endif /* IE_IMP_XML_H */
