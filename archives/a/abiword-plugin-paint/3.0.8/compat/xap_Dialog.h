/* compat/xap_Dialog.h — OHOS minimal AbiWord xap_Dialog.h shim
 * Base class for dialogs; only what the paint plugin touches.
 */
#ifndef XAP_DIALOG_H
#define XAP_DIALOG_H

#include "ut_types.h"
#include "xap_Types.h"

class XAP_DialogFactory;
class XAP_Frame;

typedef enum _XAP_Dialog_Type
{
	XAP_DLGT_NON_PERSISTENT    = 1,
	XAP_DLGT_FRAME_PERSISTENT  = 2,
	XAP_DLGT_APP_PERSISTENT    = 3,
	XAP_DLGT_MODELESS          = 4
} XAP_Dialog_Type;

class XAP_Dialog
{
public:
	XAP_Dialog (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id, const char * helpUrl = NULL);
	virtual ~XAP_Dialog (void);

	XAP_Dialog_Id    getDialogId (void) const { return m_id; }

	virtual void     runModal (XAP_Frame * pFrame) = 0;

protected:
	XAP_DialogFactory * m_pDlgFactory;
	XAP_Dialog_Id       m_id;
};

#endif /* XAP_DIALOG_H */
