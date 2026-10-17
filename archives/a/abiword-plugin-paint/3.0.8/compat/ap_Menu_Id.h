/* compat/ap_Menu_Id.h — OHOS minimal AbiWord ap_Menu_Id.h shim
 *
 * Only the two menu ids referenced by the AbiPaint plugin
 * (addToMenus anchors) are needed.  Values mirror the relative
 * ordering in the upstream ap_Menu_Id_List.h.
 */
#ifndef AP_MENU_IDSET_H
#define AP_MENU_IDSET_H

#include "xap_Types.h"

#define menuitem(id) AP_MENU_ID_##id,

enum _Ap_Menu_Id
{
	AP_MENU_ID__BOGUS1__ = 0,
	/* ... (upstream menu id list elided) ... */
	AP_MENU_ID_CONTEXT_IMAGE = 172,
	/* ... */
	AP_MENU_ID_TOOLS_WORDCOUNT = 202,
	AP_MENU_ID__BOGUS2__ = 326
};

#undef menuitem

#endif /* AP_MENU_IDSET_H */
