/* compat/xap_App.h — OHOS minimal AbiWord xap_App.h shim
 *
 * Only the API surface used by the AbiPaint plugin is provided.
 */
#ifndef XAP_APP_H
#define XAP_APP_H

#include "ut_types.h"

class AV_View;
class XAP_Frame;
class XAP_Prefs;
class XAP_Menu_Factory;
class EV_EditMethodContainer;
class EV_Menu_ActionSet;

class XAP_App
{
public:
	virtual ~XAP_App ();

	/* ---- used by AbiGeneric.cpp / AbiPaint.cpp ---- */
	XAP_Prefs *              getPrefs () const;
	EV_EditMethodContainer * getEditMethodContainer () const;
	EV_Menu_ActionSet *      getMenuActionSet () const;
	XAP_Menu_Factory *       getMenuFactory () const;
	UT_sint32                getFrameCount () const;
	XAP_Frame *              getFrame (UT_sint32 ndx) const;
	XAP_Frame *              getLastFocussedFrame () const;

	/* ---- test hook (OHOS compat shim) ---- */
	static XAP_App * getApp ();
	void             _test_clear ();

private:
	XAP_App ();
};

#endif /* XAP_APP_H */
