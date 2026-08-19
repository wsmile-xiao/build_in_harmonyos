/* compat/xap_App.h — OHOS minimal AbiWord XAP_App shim
 *
 * Backs the subset of XAP_App used by the wikipedia plugin:
 *   - a process-wide singleton (getApp)
 *   - an edit-method container (getEditMethodContainer)
 *   - a menu action set (getMenuActionSet)
 *   - a menu factory (getMenuFactory)
 *   - a frame list (getFrameCount / getFrame) — empty in the shim
 *   - openURL (records the last URL for the test hook)
 */
#ifndef XAP_APP_H
#define XAP_APP_H

#include <string>
#include "ut_types.h"
#include "ut_string_class.h"

class XAP_Frame;
class EV_EditMethodContainer;
class EV_Menu_ActionSet;
class XAP_Menu_Factory;

class ABI_EXPORT XAP_App
{
public:
	static XAP_App * getApp ();
	static void      shutdown ();

	EV_EditMethodContainer * getEditMethodContainer () const;
	EV_Menu_ActionSet *      getMenuActionSet () const;
	XAP_Menu_Factory *       getMenuFactory () const;

	UT_sint32   getFrameCount () const;
	XAP_Frame * getFrame (UT_sint32 ndx) const;
	XAP_Frame * getLastFocussedFrame () const;

	bool openURL (const char * url);

	/* ---- test hooks (OHOS compat shim) ---- */
	const char * getLastOpenedURL () const;

private:
	XAP_App ();
	~XAP_App ();

	static XAP_App * s_pInstance;

	EV_EditMethodContainer * m_pEMC;
	EV_Menu_ActionSet *      m_pActionSet;
	XAP_Menu_Factory *       m_pMenuFactory;
	std::string              m_lastURL;
};

#endif /* XAP_APP_H */
