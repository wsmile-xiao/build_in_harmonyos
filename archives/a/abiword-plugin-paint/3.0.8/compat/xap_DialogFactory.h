/* compat/xap_DialogFactory.h — OHOS minimal AbiWord xap_DialogFactory.h shim */
#ifndef XAP_DIALOGFACTORY_H
#define XAP_DIALOGFACTORY_H

#include "ut_types.h"
#include "xap_Types.h"
#include "xap_Dialog.h"

class XAP_App;
class XAP_Frame;

class XAP_DialogFactory
{
public:
	XAP_DialogFactory (XAP_App * pApp, XAP_Frame * pFrame = NULL);
	virtual ~XAP_DialogFactory (void);

	XAP_Dialog *    requestDialog (XAP_Dialog_Id id);
	void            releaseDialog (XAP_Dialog * pDialog);

private:
	XAP_App *       m_pApp;
	XAP_Frame *     m_pFrame;
};

#endif /* XAP_DIALOGFACTORY_H */
