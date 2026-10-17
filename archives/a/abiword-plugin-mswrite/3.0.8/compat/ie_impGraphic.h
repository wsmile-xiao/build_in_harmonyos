/* compat/ie_impGraphic.h — OHOS minimal IE_ImpGraphic shim
 * mswrite plugin calls IE_ImpGraphic::loadGraphic() for embedded
 * pictures; minimal stub returns UT_ERROR (pictures dropped, text import
 * unaffected) so the plugin still compiles/links.
 */
#ifndef COMPAT_IE_IMPGRAPHIC_H
#define COMPAT_IE_IMPGRAPHIC_H

#include "ut_types.h"
#include "ut_bytebuf.h"
#include "ie_types.h"
#include "fg_Graphic.h"

/* IEGraphicFileType values (ie_impGraphic.h subset, mswrite uses WMF) */
#ifndef IEGFT_WMF
#define IEGFT_WMF  ((IEGraphicFileType)2)
#endif

class IE_ImpGraphic
{
public:
	/* Stub: OHOS minimal import drops embedded pictures (text-only). */
	static UT_Error loadGraphic (UT_ByteBuf & /*pictBuf*/,
	                             IEGraphicFileType /*iType*/,
	                             FG_Graphic ** /*pFG*/)
	{
		return UT_ERROR;
	}
};

#endif /* COMPAT_IE_IMPGRAPHIC_H */
