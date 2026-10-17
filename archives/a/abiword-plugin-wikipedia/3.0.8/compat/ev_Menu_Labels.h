/* compat/ev_Menu_Labels.h — OHOS minimal AbiWord ev_Menu_Labels.h shim */
#ifndef EV_MENU_LABELS_H
#define EV_MENU_LABELS_H

#include "xap_Types.h"
#include "ut_string_class.h"

class ABI_EXPORT EV_Menu_Label
{
public:
	EV_Menu_Label (XAP_Menu_Id id, const char * szMenuLabel, const char * szStatusMsg);
	~EV_Menu_Label ();

	XAP_Menu_Id getMenuId () const;
	const char * getMenuLabel () const;
	const char * getMenuStatusMessage () const;

private:
	XAP_Menu_Id m_id;
	UT_String   m_stMenuLabel;
	UT_String   m_stStatusMsg;
};

#endif /* EV_MENU_LABELS_H */
