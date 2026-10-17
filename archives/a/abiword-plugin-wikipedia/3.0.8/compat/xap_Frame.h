/* compat/xap_Frame.h — OHOS minimal AbiWord XAP_Frame shim
 * The wikipedia plugin iterates frames calling rebuildMenus(); the shim
 * app has no frames, so XAP_Frame is only a placeholder type.
 */
#ifndef XAP_FRAME_H
#define XAP_FRAME_H

#include "ut_types.h"

class AV_View;
class XAP_App;

class ABI_EXPORT XAP_Frame
{
public:
	XAP_Frame ();
	~XAP_Frame ();

	AV_View * getCurrentView () const;
	void      rebuildMenus ();
};

#endif /* XAP_FRAME_H */
