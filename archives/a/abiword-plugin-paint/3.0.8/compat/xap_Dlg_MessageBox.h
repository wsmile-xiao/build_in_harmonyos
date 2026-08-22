/* compat/xap_Dlg_MessageBox.h — OHOS minimal
 * AbiWord xap_Dlg_MessageBox.h shim */
#ifndef XAP_DLG_MESSAGEBOX_H
#define XAP_DLG_MESSAGEBOX_H

#include "ut_types.h"
#include "xap_Dialog.h"

class XAP_DialogFactory;
class XAP_Frame;

class XAP_Dialog_MessageBox : public XAP_Dialog
{
public:
	XAP_Dialog_MessageBox (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id);
	virtual ~XAP_Dialog_MessageBox (void);

	typedef enum { b_O, b_OC, b_YN, b_YNC } tButtons;
	typedef enum { a_OK, a_CANCEL, a_YES, a_NO } tAnswer;

	virtual void    runModal (XAP_Frame * pFrame);

private:
	tButtons        m_buttons;
	tAnswer         m_answer;
};

#endif /* XAP_DLG_MESSAGEBOX_H */
