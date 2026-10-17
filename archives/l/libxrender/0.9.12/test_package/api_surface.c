#include <stddef.h>
#include <X11/extensions/Xrender.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XRenderAddGlyphs);
DECLARE_SYMBOL(XRenderAddTraps);
DECLARE_SYMBOL(XRenderChangePicture);
DECLARE_SYMBOL(XRenderComposite);
DECLARE_SYMBOL(XRenderCompositeDoublePoly);
DECLARE_SYMBOL(XRenderCompositeString16);
DECLARE_SYMBOL(XRenderCompositeString32);
DECLARE_SYMBOL(XRenderCompositeString8);
DECLARE_SYMBOL(XRenderCompositeText16);
DECLARE_SYMBOL(XRenderCompositeText32);
DECLARE_SYMBOL(XRenderCompositeText8);
DECLARE_SYMBOL(XRenderCompositeTrapezoids);
DECLARE_SYMBOL(XRenderCompositeTriangles);
DECLARE_SYMBOL(XRenderCompositeTriFan);
DECLARE_SYMBOL(XRenderCompositeTriStrip);
DECLARE_SYMBOL(XRenderCreateAnimCursor);
DECLARE_SYMBOL(XRenderCreateConicalGradient);
DECLARE_SYMBOL(XRenderCreateCursor);
DECLARE_SYMBOL(XRenderCreateGlyphSet);
DECLARE_SYMBOL(XRenderCreateLinearGradient);
DECLARE_SYMBOL(XRenderCreatePicture);
DECLARE_SYMBOL(XRenderCreateRadialGradient);
DECLARE_SYMBOL(XRenderCreateSolidFill);
DECLARE_SYMBOL(XRenderFillRectangle);
DECLARE_SYMBOL(XRenderFillRectangles);
DECLARE_SYMBOL(XRenderFindFormat);
DECLARE_SYMBOL(XRenderFindStandardFormat);
DECLARE_SYMBOL(XRenderFindVisualFormat);
DECLARE_SYMBOL(XRenderFreeGlyphs);
DECLARE_SYMBOL(XRenderFreeGlyphSet);
DECLARE_SYMBOL(XRenderFreePicture);
DECLARE_SYMBOL(XRenderParseColor);
DECLARE_SYMBOL(XRenderQueryExtension);
DECLARE_SYMBOL(XRenderQueryFilters);
DECLARE_SYMBOL(XRenderQueryFormats);
DECLARE_SYMBOL(XRenderQueryPictIndexValues);
DECLARE_SYMBOL(XRenderQuerySubpixelOrder);
DECLARE_SYMBOL(XRenderQueryVersion);
DECLARE_SYMBOL(XRenderReferenceGlyphSet);
DECLARE_SYMBOL(XRenderSetPictureClipRectangles);
DECLARE_SYMBOL(XRenderSetPictureClipRegion);
DECLARE_SYMBOL(XRenderSetPictureFilter);
DECLARE_SYMBOL(XRenderSetPictureTransform);
DECLARE_SYMBOL(XRenderSetSubpixelOrder);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    char specification[] = "rgba:f/0/8/f";
    XRenderColor color = {0};

    CHECK_SYMBOL(XRenderAddGlyphs);
    CHECK_SYMBOL(XRenderAddTraps);
    CHECK_SYMBOL(XRenderChangePicture);
    CHECK_SYMBOL(XRenderComposite);
    CHECK_SYMBOL(XRenderCompositeDoublePoly);
    CHECK_SYMBOL(XRenderCompositeString16);
    CHECK_SYMBOL(XRenderCompositeString32);
    CHECK_SYMBOL(XRenderCompositeString8);
    CHECK_SYMBOL(XRenderCompositeText16);
    CHECK_SYMBOL(XRenderCompositeText32);
    CHECK_SYMBOL(XRenderCompositeText8);
    CHECK_SYMBOL(XRenderCompositeTrapezoids);
    CHECK_SYMBOL(XRenderCompositeTriangles);
    CHECK_SYMBOL(XRenderCompositeTriFan);
    CHECK_SYMBOL(XRenderCompositeTriStrip);
    CHECK_SYMBOL(XRenderCreateAnimCursor);
    CHECK_SYMBOL(XRenderCreateConicalGradient);
    CHECK_SYMBOL(XRenderCreateCursor);
    CHECK_SYMBOL(XRenderCreateGlyphSet);
    CHECK_SYMBOL(XRenderCreateLinearGradient);
    CHECK_SYMBOL(XRenderCreatePicture);
    CHECK_SYMBOL(XRenderCreateRadialGradient);
    CHECK_SYMBOL(XRenderCreateSolidFill);
    CHECK_SYMBOL(XRenderFillRectangle);
    CHECK_SYMBOL(XRenderFillRectangles);
    CHECK_SYMBOL(XRenderFindFormat);
    CHECK_SYMBOL(XRenderFindStandardFormat);
    CHECK_SYMBOL(XRenderFindVisualFormat);
    CHECK_SYMBOL(XRenderFreeGlyphs);
    CHECK_SYMBOL(XRenderFreeGlyphSet);
    CHECK_SYMBOL(XRenderFreePicture);
    CHECK_SYMBOL(XRenderParseColor);
    CHECK_SYMBOL(XRenderQueryExtension);
    CHECK_SYMBOL(XRenderQueryFilters);
    CHECK_SYMBOL(XRenderQueryFormats);
    CHECK_SYMBOL(XRenderQueryPictIndexValues);
    CHECK_SYMBOL(XRenderQuerySubpixelOrder);
    CHECK_SYMBOL(XRenderQueryVersion);
    CHECK_SYMBOL(XRenderReferenceGlyphSet);
    CHECK_SYMBOL(XRenderSetPictureClipRectangles);
    CHECK_SYMBOL(XRenderSetPictureClipRegion);
    CHECK_SYMBOL(XRenderSetPictureFilter);
    CHECK_SYMBOL(XRenderSetPictureTransform);
    CHECK_SYMBOL(XRenderSetSubpixelOrder);

    if (!XRenderParseColor(NULL, specification, &color) ||
        color.red != 0xffff || color.green != 0 || color.blue != 0x8888 ||
        color.alpha != 0xffff) {
        return 1;
    }
    return 0;
}
