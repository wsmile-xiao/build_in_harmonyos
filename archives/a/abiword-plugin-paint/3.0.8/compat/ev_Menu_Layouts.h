/* compat/ev_Menu_Layouts.h — OHOS minimal AbiWord ev_Menu_Layouts.h shim */
#ifndef EV_MENU_LAYOUTS_H
#define EV_MENU_LAYOUTS_H

#include "ut_types.h"
#include "xap_Types.h"

typedef enum _ev_Menu_LayoutFlags
{
	EV_MLF_Normal,
	EV_MLF_BeginSubMenu,
	EV_MLF_EndSubMenu,
	EV_MLF_BeginPopupMenu,
	EV_MLF_EndPopupMenu,
	EV_MLF_Separator

} EV_Menu_LayoutFlags;

#endif /* EV_MENU_LAYOUTS_H */
