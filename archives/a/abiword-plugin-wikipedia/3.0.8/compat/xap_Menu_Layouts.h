/* compat/xap_Menu_Layouts.h — OHOS minimal AbiWord menu-factory shim
 *
 * XAP_Menu_Factory implements the four operations the wikipedia plugin
 * uses (addNewMenuAfter / addNewLabel on register, removeMenuItem on
 * unregister) and keeps the registered label→id mapping observable so
 * the end-to-end test can assert the "Wi&ki Encyclopedia" menu item.
 */
#ifndef XAP_MENU_LAYOUTS_H
#define XAP_MENU_LAYOUTS_H

#include <vector>
#include <utility>
#include "ut_types.h"
#include "ut_string_class.h"
#include "xap_Types.h"
#include "ev_Menu_Layouts.h"

class XAP_App;
class EV_Menu_LabelSet;

class ABI_EXPORT XAP_Menu_Factory
{
public:
	XAP_Menu_Factory (XAP_App * pApp);
	~XAP_Menu_Factory ();

	XAP_Menu_Id addNewMenuAfter (const char * szMenu,
	                             const char * szLanguage,
	                             const XAP_Menu_Id afterID,
	                             EV_Menu_LayoutFlags flags,
	                             XAP_Menu_Id newID = 0);
	XAP_Menu_Id addNewMenuAfter (const char * szMenu,
	                             const char * szLanguage,
	                             const char * szAfter,
	                             EV_Menu_LayoutFlags flags,
	                             XAP_Menu_Id menuID = 0);
	XAP_Menu_Id removeMenuItem (const char * szMenu,
	                            const char * szLanguage,
	                            const char * szNuke);
	XAP_Menu_Id removeMenuItem (const char * szMenu,
	                            const char * szLanguage,
	                            XAP_Menu_Id nukeID);
	bool        addNewLabel (const char * szMenu,
	                         XAP_Menu_Id newID,
	                         const char * szNewLabel,
	                         const char * szNewTooltip);

	/* ---- test hooks (OHOS compat shim) ---- */
	bool        hasLabel (const char * szNewLabel) const;
	XAP_Menu_Id getIDForLabel (const char * szNewLabel) const;

private:
	XAP_App *   m_pApp;
	XAP_Menu_Id m_maxID;
	std::vector<std::pair<UT_String, XAP_Menu_Id> > m_labels;
};

#endif /* XAP_MENU_LAYOUTS_H */
