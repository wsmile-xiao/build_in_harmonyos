/* compat/ev_Menu_Actions.h — OHOS minimal AbiWord ev_Menu_Actions.h shim */
#ifndef EV_MENU_ACTIONS_H
#define EV_MENU_ACTIONS_H

#include "ut_types.h"
#include "xap_Types.h"

class AV_View;
class EV_Menu_Label;

typedef enum _ev_Menu_ItemState
{
	EV_MIS_ZERO   = 0x00,
	EV_MIS_Gray   = 0x01,
	EV_MIS_Toggled = 0x02,
	EV_MIS_Bold   = 0x04

} EV_Menu_ItemState;

typedef EV_Menu_ItemState (*EV_GetMenuItemState_pFn)(AV_View * pView, XAP_Menu_Id id);
typedef const char * (*EV_GetMenuItemComputedLabel_pFn)(const EV_Menu_Label * pLabel, XAP_Menu_Id id);

#define Defun_EV_GetMenuItemComputedLabel_Fn(fn) ABI_EXPORT const char * fn(const EV_Menu_Label * pLabel, XAP_Menu_Id id)

class EV_Menu_Action
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

	XAP_Menu_Id                    getMenuId () const;
	const char *                   getMethodName () const;
	bool                           raisesDialog () const;
	bool                           isCheckable () const;
	bool                           isRadio () const;
	bool                           hasGetStateFunction () const;
	bool                           hasDynamicLabel () const;
	EV_Menu_ItemState              getMenuItemState (AV_View * pView) const;
	const char *                   getDynamicLabel (const EV_Menu_Label * pLabel) const;

private:
	XAP_Menu_Id                    m_id;
	bool                           m_bHoldsSubMenu;
	bool                           m_bRaisesDialog;
	bool                           m_bCheckable;
	bool                           m_bRadio;
	char *                         m_szMethodName;
	EV_GetMenuItemState_pFn        m_pfnGetState;
	EV_GetMenuItemComputedLabel_pFn m_pfnGetLabel;
	UT_String                      m_stScriptName;
};

class EV_Menu_ActionSet
{
public:
	EV_Menu_ActionSet ();
	~EV_Menu_ActionSet ();

	bool               addAction (EV_Menu_Action * pAction);
	const EV_Menu_Action * getAction (XAP_Menu_Id id) const;
	UT_uint32          getActionCount () const;

private:
	UT_GenericVector<EV_Menu_Action *> m_actionTable;
};

#endif /* EV_MENU_ACTIONS_H */
