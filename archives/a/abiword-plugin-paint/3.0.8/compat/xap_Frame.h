/* compat/xap_Frame.h — OHOS minimal AbiWord xap_Frame.h shim */
#ifndef XAP_FRAME_H
#define XAP_FRAME_H

#include "ut_types.h"
#include "xap_Types.h"
#include "xap_Dlg_MessageBox.h"

class AV_View;
class XAP_DialogFactory;

class XAP_Frame
{
public:
	XAP_Frame ();
	virtual ~XAP_Frame ();

	AV_View *            getCurrentView () const;
	XAP_DialogFactory *  getDialogFactory ();
	void                 nullUpdate () const;
	const char *         getFilename () const;
	void                 rebuildMenus ();
	XAP_Dialog_MessageBox::tAnswer
	                     showMessageBox (const char * sz,
	                                     XAP_Dialog_MessageBox::tButtons buttons,
	                                     XAP_Dialog_MessageBox::tAnswer answer);

	/* ---- test hook (OHOS compat shim) ---- */
	void                 _test_setCurrentView (AV_View * v);
};

#endif /* XAP_FRAME_H */
