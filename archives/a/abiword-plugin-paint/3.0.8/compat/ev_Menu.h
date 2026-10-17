/* compat/ev_Menu.h — OHOS minimal AbiWord ev_Menu.h shim
 * The AbiPaint plugin includes this header but does not use EV_Menu
 * directly; only a forward declaration is needed.
 */
#ifndef EV_MENU_H
#define EV_MENU_H

class XAP_App;

class EV_Menu
{
public:
	virtual ~EV_Menu ();
};

#endif /* EV_MENU_H */
