/* compat/ev_Menu_Actions.h — OHOS minimal AbiWord menu-action shim
 *
 * The wikipedia plugin creates one EV_Menu_Action and registers it in the
 * app's EV_Menu_ActionSet so the menu layout id maps to the
 * "Wikipedia_invoke" edit method.
 */
#ifndef EV_MENU_ACTIONS_H
#define EV_MENU_ACTIONS_H

#include <vector>
#include "ut_types.h"
#include "ut_string_class.h"
#include "xap_Types.h"

class AV_View;
class EV_Menu_Label;

typedef int EV_Menu_ItemState;
typedef EV_Menu_ItemState (*EV_GetMenuItemState_pFn)(AV_View * pView, XAP_Menu_Id id);
typedef const char * (*EV_GetMenuItemComputedLabel_pFn)(const EV_Menu_Label * pLabel, XAP_Menu_Id id);

class ABI_EXPORT EV_Menu_Action
{
public:
	EV_Menu_Action (XAP_Menu_Id id,
	                bool bHoldsSubMenu,
	                bool bRaisesDialog,
	                bool bCheckable,
	                bool bRadio,
	                const char * szMethodName,
	                EV_GetMenuItemState_pFn pfnGetState,
	                EV_GetMenuItemComputedLabel_pFn pfnGetLabel,
	                const UT_String & stScriptName = UT_String ());
	~EV_Menu_Action ();

	XAP_Menu_Id getMenuId () const;
	const char * getMethodName () const;
	bool         raisesDialog () const;

private:
	XAP_Menu_Id m_id;
	bool        m_bHoldsSubMenu;
	bool        m_bRaisesDialog;
	bool        m_bCheckable;
	bool        m_bRadio;
	char *      m_szMethodName;
	EV_GetMenuItemState_pFn         m_pfnGetState;
	EV_GetMenuItemComputedLabel_pFn m_pfnGetLabel;
	UT_String   m_stScriptName;
};

class ABI_EXPORT EV_Menu_ActionSet
{
public:
	EV_Menu_ActionSet ();
	~EV_Menu_ActionSet ();

	bool                    addAction (EV_Menu_Action * pAction);
	const EV_Menu_Action *  getAction (XAP_Menu_Id id) const;
	UT_uint32               countActions () const;

private:
	std::vector<EV_Menu_Action *> m_vec;
};

#endif /* EV_MENU_ACTIONS_H */
