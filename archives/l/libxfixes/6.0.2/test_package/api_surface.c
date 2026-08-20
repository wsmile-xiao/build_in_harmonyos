#include <stddef.h>
#include <X11/extensions/Xfixes.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

DECLARE_SYMBOL(XFixesQueryExtension);
DECLARE_SYMBOL(XFixesQueryVersion);
DECLARE_SYMBOL(XFixesVersion);
DECLARE_SYMBOL(XFixesChangeSaveSet);
DECLARE_SYMBOL(XFixesSelectSelectionInput);
DECLARE_SYMBOL(XFixesSelectCursorInput);
DECLARE_SYMBOL(XFixesGetCursorImage);
DECLARE_SYMBOL(XFixesCreateRegion);
DECLARE_SYMBOL(XFixesCreateRegionFromBitmap);
DECLARE_SYMBOL(XFixesCreateRegionFromWindow);
DECLARE_SYMBOL(XFixesCreateRegionFromGC);
DECLARE_SYMBOL(XFixesCreateRegionFromPicture);
DECLARE_SYMBOL(XFixesDestroyRegion);
DECLARE_SYMBOL(XFixesSetRegion);
DECLARE_SYMBOL(XFixesCopyRegion);
DECLARE_SYMBOL(XFixesUnionRegion);
DECLARE_SYMBOL(XFixesIntersectRegion);
DECLARE_SYMBOL(XFixesSubtractRegion);
DECLARE_SYMBOL(XFixesInvertRegion);
DECLARE_SYMBOL(XFixesTranslateRegion);
DECLARE_SYMBOL(XFixesRegionExtents);
DECLARE_SYMBOL(XFixesFetchRegion);
DECLARE_SYMBOL(XFixesFetchRegionAndBounds);
DECLARE_SYMBOL(XFixesSetGCClipRegion);
DECLARE_SYMBOL(XFixesSetWindowShapeRegion);
DECLARE_SYMBOL(XFixesSetPictureClipRegion);
DECLARE_SYMBOL(XFixesSetCursorName);
DECLARE_SYMBOL(XFixesGetCursorName);
DECLARE_SYMBOL(XFixesChangeCursor);
DECLARE_SYMBOL(XFixesChangeCursorByName);
DECLARE_SYMBOL(XFixesExpandRegion);
DECLARE_SYMBOL(XFixesHideCursor);
DECLARE_SYMBOL(XFixesShowCursor);
DECLARE_SYMBOL(XFixesCreatePointerBarrier);
DECLARE_SYMBOL(XFixesDestroyPointerBarrier);
DECLARE_SYMBOL(XFixesSetClientDisconnectMode);
DECLARE_SYMBOL(XFixesGetClientDisconnectMode);

#define CHECK_SYMBOL(name) \
    do { \
        if (probe_##name == NULL) { \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    CHECK_SYMBOL(XFixesQueryExtension);
    CHECK_SYMBOL(XFixesQueryVersion);
    CHECK_SYMBOL(XFixesVersion);
    CHECK_SYMBOL(XFixesChangeSaveSet);
    CHECK_SYMBOL(XFixesSelectSelectionInput);
    CHECK_SYMBOL(XFixesSelectCursorInput);
    CHECK_SYMBOL(XFixesGetCursorImage);
    CHECK_SYMBOL(XFixesCreateRegion);
    CHECK_SYMBOL(XFixesCreateRegionFromBitmap);
    CHECK_SYMBOL(XFixesCreateRegionFromWindow);
    CHECK_SYMBOL(XFixesCreateRegionFromGC);
    CHECK_SYMBOL(XFixesCreateRegionFromPicture);
    CHECK_SYMBOL(XFixesDestroyRegion);
    CHECK_SYMBOL(XFixesSetRegion);
    CHECK_SYMBOL(XFixesCopyRegion);
    CHECK_SYMBOL(XFixesUnionRegion);
    CHECK_SYMBOL(XFixesIntersectRegion);
    CHECK_SYMBOL(XFixesSubtractRegion);
    CHECK_SYMBOL(XFixesInvertRegion);
    CHECK_SYMBOL(XFixesTranslateRegion);
    CHECK_SYMBOL(XFixesRegionExtents);
    CHECK_SYMBOL(XFixesFetchRegion);
    CHECK_SYMBOL(XFixesFetchRegionAndBounds);
    CHECK_SYMBOL(XFixesSetGCClipRegion);
    CHECK_SYMBOL(XFixesSetWindowShapeRegion);
    CHECK_SYMBOL(XFixesSetPictureClipRegion);
    CHECK_SYMBOL(XFixesSetCursorName);
    CHECK_SYMBOL(XFixesGetCursorName);
    CHECK_SYMBOL(XFixesChangeCursor);
    CHECK_SYMBOL(XFixesChangeCursorByName);
    CHECK_SYMBOL(XFixesExpandRegion);
    CHECK_SYMBOL(XFixesHideCursor);
    CHECK_SYMBOL(XFixesShowCursor);
    CHECK_SYMBOL(XFixesCreatePointerBarrier);
    CHECK_SYMBOL(XFixesDestroyPointerBarrier);
    CHECK_SYMBOL(XFixesSetClientDisconnectMode);
    CHECK_SYMBOL(XFixesGetClientDisconnectMode);
    return XFixesVersion() == XFIXES_VERSION ? 0 : 1;
}
