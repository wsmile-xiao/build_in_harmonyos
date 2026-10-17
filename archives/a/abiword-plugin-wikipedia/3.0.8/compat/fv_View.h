/* compat/fv_View.h — OHOS minimal AbiWord view shim
 *
 * The wikipedia plugin's invoke callback selects the word under the
 * cursor and reads its text.  The shim records the selected text so a
 * test can drive the full register → invoke → openURL path.
 */
#ifndef FV_VIEW_H
#define FV_VIEW_H

#include "ut_types.h"
#include "ev_EditMethod.h"

class ABI_EXPORT AV_View
{
public:
	AV_View ();
	virtual ~AV_View ();
};

typedef enum _FV_DocPos
{
	FV_DOCPOS_BOW,
	FV_DOCPOS_EOW_MOVE,
	FV_DOCPOS_EOW_SELECT
} FV_DocPos;

class ABI_EXPORT FV_View : public AV_View
{
public:
	FV_View ();
	virtual ~FV_View ();

	void moveInsPtTo (FV_DocPos dp, bool bClearSelection = true);
	void extSelTo (FV_DocPos dp);
	bool isSelectionEmpty (void) const;
	void getSelectionText (UT_UCS4Char *& text) const;

	/* ---- test hooks (OHOS compat shim) ---- */
	void setSelectionText (const UT_UCS4Char * text);

private:
	bool          m_selectionEmpty;
	UT_UCS4Char * m_selectionText;
};

#endif /* FV_VIEW_H */
