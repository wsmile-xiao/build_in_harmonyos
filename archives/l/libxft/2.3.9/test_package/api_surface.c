#include <stddef.h>
#include <stdio.h>
#include <X11/Xft/Xft.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XftCharExists);
DECLARE_SYMBOL(XftCharFontSpecRender);
DECLARE_SYMBOL(XftCharIndex);
DECLARE_SYMBOL(XftCharSpecRender);
DECLARE_SYMBOL(XftColorAllocName);
DECLARE_SYMBOL(XftColorAllocValue);
DECLARE_SYMBOL(XftColorFree);
DECLARE_SYMBOL(XftDefaultHasRender);
DECLARE_SYMBOL(XftDefaultSet);
DECLARE_SYMBOL(XftDefaultSubstitute);
DECLARE_SYMBOL(XftDrawChange);
DECLARE_SYMBOL(XftDrawCharFontSpec);
DECLARE_SYMBOL(XftDrawCharSpec);
DECLARE_SYMBOL(XftDrawColormap);
DECLARE_SYMBOL(XftDrawCreate);
DECLARE_SYMBOL(XftDrawCreateAlpha);
DECLARE_SYMBOL(XftDrawCreateBitmap);
DECLARE_SYMBOL(XftDrawDestroy);
DECLARE_SYMBOL(XftDrawDisplay);
DECLARE_SYMBOL(XftDrawDrawable);
DECLARE_SYMBOL(XftDrawGlyphFontSpec);
DECLARE_SYMBOL(XftDrawGlyphs);
DECLARE_SYMBOL(XftDrawGlyphSpec);
DECLARE_SYMBOL(XftDrawPicture);
DECLARE_SYMBOL(XftDrawRect);
DECLARE_SYMBOL(XftDrawSetClip);
DECLARE_SYMBOL(XftDrawSetClipRectangles);
DECLARE_SYMBOL(XftDrawSetSubwindowMode);
DECLARE_SYMBOL(XftDrawSrcPicture);
DECLARE_SYMBOL(XftDrawString16);
DECLARE_SYMBOL(XftDrawString32);
DECLARE_SYMBOL(XftDrawString8);
DECLARE_SYMBOL(XftDrawStringUtf16);
DECLARE_SYMBOL(XftDrawStringUtf8);
DECLARE_SYMBOL(XftDrawVisual);
DECLARE_SYMBOL(XftFontCheckGlyph);
DECLARE_SYMBOL(XftFontClose);
DECLARE_SYMBOL(XftFontCopy);
DECLARE_SYMBOL(XftFontInfoCreate);
DECLARE_SYMBOL(XftFontInfoDestroy);
DECLARE_SYMBOL(XftFontInfoEqual);
DECLARE_SYMBOL(XftFontInfoHash);
DECLARE_SYMBOL(XftFontLoadGlyphs);
DECLARE_SYMBOL(XftFontMatch);
DECLARE_SYMBOL(XftFontOpen);
DECLARE_SYMBOL(XftFontOpenInfo);
DECLARE_SYMBOL(XftFontOpenName);
DECLARE_SYMBOL(XftFontOpenPattern);
DECLARE_SYMBOL(XftFontOpenXlfd);
DECLARE_SYMBOL(XftFontUnloadGlyphs);
DECLARE_SYMBOL(XftGetVersion);
DECLARE_SYMBOL(XftGlyphExtents);
DECLARE_SYMBOL(XftGlyphFontSpecRender);
DECLARE_SYMBOL(XftGlyphRender);
DECLARE_SYMBOL(XftGlyphSpecRender);
DECLARE_SYMBOL(XftInit);
DECLARE_SYMBOL(XftInitFtLibrary);
DECLARE_SYMBOL(XftListFonts);
DECLARE_SYMBOL(XftLockFace);
DECLARE_SYMBOL(XftNameParse);
DECLARE_SYMBOL(XftNameUnparse);
DECLARE_SYMBOL(XftTextExtents16);
DECLARE_SYMBOL(XftTextExtents32);
DECLARE_SYMBOL(XftTextExtents8);
DECLARE_SYMBOL(XftTextExtentsUtf16);
DECLARE_SYMBOL(XftTextExtentsUtf8);
DECLARE_SYMBOL(XftTextRender16);
DECLARE_SYMBOL(XftTextRender16BE);
DECLARE_SYMBOL(XftTextRender16LE);
DECLARE_SYMBOL(XftTextRender32);
DECLARE_SYMBOL(XftTextRender32BE);
DECLARE_SYMBOL(XftTextRender32LE);
DECLARE_SYMBOL(XftTextRender8);
DECLARE_SYMBOL(XftTextRenderUtf16);
DECLARE_SYMBOL(XftTextRenderUtf8);
DECLARE_SYMBOL(XftUnlockFace);
DECLARE_SYMBOL(XftXlfdParse);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

#define CHECK_TRUE(value, code) \
    do { \
        if (!(value)) { \
            return (code); \
        } \
    } while (0)

int main(void)
{
    CHECK_SYMBOL(XftCharExists);
    CHECK_SYMBOL(XftCharFontSpecRender);
    CHECK_SYMBOL(XftCharIndex);
    CHECK_SYMBOL(XftCharSpecRender);
    CHECK_SYMBOL(XftColorAllocName);
    CHECK_SYMBOL(XftColorAllocValue);
    CHECK_SYMBOL(XftColorFree);
    CHECK_SYMBOL(XftDefaultHasRender);
    CHECK_SYMBOL(XftDefaultSet);
    CHECK_SYMBOL(XftDefaultSubstitute);
    CHECK_SYMBOL(XftDrawChange);
    CHECK_SYMBOL(XftDrawCharFontSpec);
    CHECK_SYMBOL(XftDrawCharSpec);
    CHECK_SYMBOL(XftDrawColormap);
    CHECK_SYMBOL(XftDrawCreate);
    CHECK_SYMBOL(XftDrawCreateAlpha);
    CHECK_SYMBOL(XftDrawCreateBitmap);
    CHECK_SYMBOL(XftDrawDestroy);
    CHECK_SYMBOL(XftDrawDisplay);
    CHECK_SYMBOL(XftDrawDrawable);
    CHECK_SYMBOL(XftDrawGlyphFontSpec);
    CHECK_SYMBOL(XftDrawGlyphs);
    CHECK_SYMBOL(XftDrawGlyphSpec);
    CHECK_SYMBOL(XftDrawPicture);
    CHECK_SYMBOL(XftDrawRect);
    CHECK_SYMBOL(XftDrawSetClip);
    CHECK_SYMBOL(XftDrawSetClipRectangles);
    CHECK_SYMBOL(XftDrawSetSubwindowMode);
    CHECK_SYMBOL(XftDrawSrcPicture);
    CHECK_SYMBOL(XftDrawString16);
    CHECK_SYMBOL(XftDrawString32);
    CHECK_SYMBOL(XftDrawString8);
    CHECK_SYMBOL(XftDrawStringUtf16);
    CHECK_SYMBOL(XftDrawStringUtf8);
    CHECK_SYMBOL(XftDrawVisual);
    CHECK_SYMBOL(XftFontCheckGlyph);
    CHECK_SYMBOL(XftFontClose);
    CHECK_SYMBOL(XftFontCopy);
    CHECK_SYMBOL(XftFontInfoCreate);
    CHECK_SYMBOL(XftFontInfoDestroy);
    CHECK_SYMBOL(XftFontInfoEqual);
    CHECK_SYMBOL(XftFontInfoHash);
    CHECK_SYMBOL(XftFontLoadGlyphs);
    CHECK_SYMBOL(XftFontMatch);
    CHECK_SYMBOL(XftFontOpen);
    CHECK_SYMBOL(XftFontOpenInfo);
    CHECK_SYMBOL(XftFontOpenName);
    CHECK_SYMBOL(XftFontOpenPattern);
    CHECK_SYMBOL(XftFontOpenXlfd);
    CHECK_SYMBOL(XftFontUnloadGlyphs);
    CHECK_SYMBOL(XftGetVersion);
    CHECK_SYMBOL(XftGlyphExtents);
    CHECK_SYMBOL(XftGlyphFontSpecRender);
    CHECK_SYMBOL(XftGlyphRender);
    CHECK_SYMBOL(XftGlyphSpecRender);
    CHECK_SYMBOL(XftInit);
    CHECK_SYMBOL(XftInitFtLibrary);
    CHECK_SYMBOL(XftListFonts);
    CHECK_SYMBOL(XftLockFace);
    CHECK_SYMBOL(XftNameParse);
    CHECK_SYMBOL(XftNameUnparse);
    CHECK_SYMBOL(XftTextExtents16);
    CHECK_SYMBOL(XftTextExtents32);
    CHECK_SYMBOL(XftTextExtents8);
    CHECK_SYMBOL(XftTextExtentsUtf16);
    CHECK_SYMBOL(XftTextExtentsUtf8);
    CHECK_SYMBOL(XftTextRender16);
    CHECK_SYMBOL(XftTextRender16BE);
    CHECK_SYMBOL(XftTextRender16LE);
    CHECK_SYMBOL(XftTextRender32);
    CHECK_SYMBOL(XftTextRender32BE);
    CHECK_SYMBOL(XftTextRender32LE);
    CHECK_SYMBOL(XftTextRender8);
    CHECK_SYMBOL(XftTextRenderUtf16);
    CHECK_SYMBOL(XftTextRenderUtf8);
    CHECK_SYMBOL(XftUnlockFace);
    CHECK_SYMBOL(XftXlfdParse);

    CHECK_TRUE(XftGetVersion() == XFT_VERSION, 201);
    CHECK_TRUE(XftInitFtLibrary(), 202);
    puts("LIBXFT_API_SURFACE_PASS assertions=79");
    return 0;
}
