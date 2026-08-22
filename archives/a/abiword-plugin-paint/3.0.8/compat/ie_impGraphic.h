/* compat/ie_impGraphic.h — OHOS minimal AbiWord ie_impGraphic.h shim
 *
 * AbiPaint.cpp uses IE_ImpGraphic::loadGraphic() and the FG_Graphic
 * type.
 */
#ifndef IE_IMPGGRAPHIC_H
#define IE_IMPGGRAPHIC_H

#include "ut_types.h"
#include "ie_types.h"

class FG_Graphic;

class IE_ImpGraphic
{
public:
	virtual ~IE_ImpGraphic () {}

	static UT_Error loadGraphic (const char * szFilename,
	                             IEGraphicFileType iegft,
	                             FG_Graphic ** ppfg);
};

#endif /* IE_IMPGGRAPHIC_H */
