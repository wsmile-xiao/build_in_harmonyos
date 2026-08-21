/* compat/fg_Graphic.h — OHOS minimal FG_Graphic shim
 * The mswrite plugin calls IE_ImpGraphic::loadGraphic() for embedded
 * pictures; on OHOS the graphic is not retained (mswrite import is
 * text-focused), so FG_Graphic is a minimal marker base with empty
 * buffer/mime accessors.
 */
#ifndef COMPAT_FG_GRAPHIC_H
#define COMPAT_FG_GRAPHIC_H

#include <string>
#include "ut_types.h"
#include "ut_bytebuf.h"

class FG_Graphic
{
public:
	virtual ~FG_Graphic () {}

	virtual const std::string & getMimeType () const
	{
		static const std::string empty;
		return empty;
	}

	virtual const UT_ByteBuf * getBuffer () const { return 0; }
};

#endif /* COMPAT_FG_GRAPHIC_H */
