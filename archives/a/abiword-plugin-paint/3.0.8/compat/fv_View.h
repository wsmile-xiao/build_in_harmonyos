/* compat/fv_View.h — OHOS minimal AbiWord fv_View.h shim
 *
 * FV_View — the paint plugin uses saveSelectedImage / getSelectedImage /
 * cmdUnselectSelection / setPoint / extSelHorizontal / cmdInsertGraphic.
 * The shim records an inserted graphic count so tests can verify that
 * cmdInsertGraphic was invoked.
 */
#ifndef FV_VIEW_H
#define FV_VIEW_H

#include "ut_types.h"
#include "av_View.h"
#include "fg_Graphic.h"

typedef UT_uint32 PT_DocPosition;

class FV_View : public AV_View
{
public:
	FV_View ();
	virtual ~FV_View ();

	PT_DocPosition saveSelectedImage (const char * toFile);
	PT_DocPosition getSelectedImage (const char ** dataId) const;
	void           cmdUnselectSelection (void);
	void           setPoint (UT_uint32 pt);
	void           extSelHorizontal (bool bForward, UT_uint32 count);
	UT_Error       cmdInsertGraphic (FG_Graphic * pFG);

	/* ---- test hook (OHOS compat shim) ---- */
	UT_uint32      _test_insertedGraphicCount () const { return m_inserted; }

private:
	UT_uint32      m_inserted;
};

#endif /* FV_VIEW_H */
