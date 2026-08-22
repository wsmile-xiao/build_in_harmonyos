/* compat/xap_Dlg_FileOpenSaveAs.h — OHOS minimal
 * AbiWord xap_Dlg_FileOpenSaveAs.h shim */
#ifndef XAP_DLG_FILEOPENSAVEAS_H
#define XAP_DLG_FILEOPENSAVEAS_H

#include "ut_types.h"
#include "xap_Dialog.h"
#include "xap_DialogFactory.h"

class XAP_Frame;

class XAP_Dialog_FileOpenSaveAs : public XAP_Dialog
{
public:
	XAP_Dialog_FileOpenSaveAs (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id);
	virtual ~XAP_Dialog_FileOpenSaveAs (void);

	typedef enum { a_VOID, a_OK, a_CANCEL } tAnswer;

	virtual void    runModal (XAP_Frame * pFrame);

	void            setCurrentPathname (const char * szPathname);
	void            setSuggestFilename (bool bSuggest);
	void            setFileTypeList (const char ** szDescriptions,
	                                 const char ** szSuffixes,
	                                 const UT_sint32 * nTypeList);
	tAnswer         getAnswer (void) const;
	const char *    getPathname (void) const;

private:
	char *          m_szFinalPathname;
	tAnswer         m_answer;
};

#endif /* XAP_DLG_FILEOPENSAVEAS_H */
