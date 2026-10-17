/* compat/xap_Menu_Layouts.h — OHOS minimal AbiWord xap_Menu_Layouts.h shim
 *
 * XAP_Menu_Factory — the paint plugin's addToMenus/removeFromMenus use
 * getNewID/addNewLabel/addNewMenuAfter/removeMenuItem.  The shim keeps a
 * registry of added menu ids so a test can verify registration.
 */
#ifndef XAP_MENU_LAYOUTS_H
#define XAP_MENU_LAYOUTS_H

#include "ut_types.h"
#include "ut_vector.h"
#include "xap_Types.h"
#include "ev_Menu_Layouts.h"

class XAP_App;
class EV_Menu_LabelSet;

class XAP_Menu_Factory
{
public:
	XAP_Menu_Factory (XAP_App * pApp);
	~XAP_Menu_Factory (void);

	XAP_Menu_Id     getNewID (void);
	bool            addNewLabel (const char * szMenu, XAP_Menu_Id newID,
	                             const char * szNewLabel, const char * szNewTooltip);
	XAP_Menu_Id     addNewMenuAfter (const char * szMenu, const char * szLanguage,
	                                 const XAP_Menu_Id afterID,
	                                 EV_Menu_LayoutFlags flags, XAP_Menu_Id newID = 0);
	XAP_Menu_Id     removeMenuItem (const char * szMenu, const char * szLanguage,
	                                XAP_Menu_Id nukeID);

	/* ---- test hook (OHOS compat shim) ---- */
	UT_uint32       _test_menuCount () const;

private:
	XAP_App *       m_pApp;
	XAP_Menu_Id     m_maxID;
	UT_GenericVector<XAP_Menu_Id> m_menuItems;
};

#endif /* XAP_MENU_LAYOUTS_H */
