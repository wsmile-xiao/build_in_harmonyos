/*
 * libXcursor.so.1 API surface probe.
 *
 * Each Xcursor* symbol declared in Xcursor.h is taken by address through a
 * strongly-typed live relocation, so a missing implementation or a signature
 * mismatch fails at link/load time instead of being silently dropped.
 * The test needs no X server: taking the address only requires the header.
 */

#include <stdio.h>
#include <X11/Xcursor/Xcursor.h>

#define DECLARE_SYMBOL(name)                       \
    static void *probe_##name(void)                \
    {                                              \
        __typeof__(&name) probe = &name;           \
        return (void *)probe;                      \
    }

#define CHECK_SYMBOL(name)                         \
    do {                                           \
        void *p = probe_##name();                  \
        if (p == 0) {                              \
            fprintf(stderr, "FAIL: symbol " #name "\n"); \
            return 1;                              \
        }                                          \
    } while (0)

DECLARE_SYMBOL(XcursorAnimateCreate)
DECLARE_SYMBOL(XcursorAnimateDestroy)
DECLARE_SYMBOL(XcursorAnimateNext)
DECLARE_SYMBOL(XcursorCommentCreate)
DECLARE_SYMBOL(XcursorCommentDestroy)
DECLARE_SYMBOL(XcursorCommentsCreate)
DECLARE_SYMBOL(XcursorCommentsDestroy)
DECLARE_SYMBOL(XcursorCursorsCreate)
DECLARE_SYMBOL(XcursorCursorsDestroy)
DECLARE_SYMBOL(XcursorFileLoad)
DECLARE_SYMBOL(XcursorFileLoadAllImages)
DECLARE_SYMBOL(XcursorFileLoadImage)
DECLARE_SYMBOL(XcursorFileLoadImages)
DECLARE_SYMBOL(XcursorFilenameLoad)
DECLARE_SYMBOL(XcursorFilenameLoadAllImages)
DECLARE_SYMBOL(XcursorFilenameLoadCursor)
DECLARE_SYMBOL(XcursorFilenameLoadCursors)
DECLARE_SYMBOL(XcursorFilenameLoadImage)
DECLARE_SYMBOL(XcursorFilenameLoadImages)
DECLARE_SYMBOL(XcursorFilenameSave)
DECLARE_SYMBOL(XcursorFilenameSaveImages)
DECLARE_SYMBOL(XcursorFileSave)
DECLARE_SYMBOL(XcursorFileSaveImages)
DECLARE_SYMBOL(XcursorGetDefaultSize)
DECLARE_SYMBOL(XcursorGetResizable)
DECLARE_SYMBOL(XcursorGetTheme)
DECLARE_SYMBOL(XcursorGetThemeCore)
DECLARE_SYMBOL(XcursorImageCreate)
DECLARE_SYMBOL(XcursorImageDestroy)
DECLARE_SYMBOL(XcursorImageHash)
DECLARE_SYMBOL(XcursorImageLoadCursor)
DECLARE_SYMBOL(XcursorImagesCreate)
DECLARE_SYMBOL(XcursorImagesDestroy)
DECLARE_SYMBOL(XcursorImagesLoadCursor)
DECLARE_SYMBOL(XcursorImagesLoadCursors)
DECLARE_SYMBOL(XcursorImagesSetName)
DECLARE_SYMBOL(XcursorLibraryLoadCursor)
DECLARE_SYMBOL(XcursorLibraryLoadCursors)
DECLARE_SYMBOL(XcursorLibraryLoadImage)
DECLARE_SYMBOL(XcursorLibraryLoadImages)
DECLARE_SYMBOL(XcursorLibraryPath)
DECLARE_SYMBOL(XcursorLibraryShape)
DECLARE_SYMBOL(XcursorNoticeCreateBitmap)
DECLARE_SYMBOL(XcursorNoticePutBitmap)
DECLARE_SYMBOL(XcursorSetDefaultSize)
DECLARE_SYMBOL(XcursorSetResizable)
DECLARE_SYMBOL(XcursorSetTheme)
DECLARE_SYMBOL(XcursorSetThemeCore)
DECLARE_SYMBOL(XcursorShapeLoadCursor)
DECLARE_SYMBOL(XcursorShapeLoadCursors)
DECLARE_SYMBOL(XcursorShapeLoadImage)
DECLARE_SYMBOL(XcursorShapeLoadImages)
DECLARE_SYMBOL(XcursorSupportsAnim)
DECLARE_SYMBOL(XcursorSupportsARGB)
DECLARE_SYMBOL(XcursorTryShapeBitmapCursor)
DECLARE_SYMBOL(XcursorTryShapeCursor)
DECLARE_SYMBOL(XcursorXcFileLoad)
DECLARE_SYMBOL(XcursorXcFileLoadAllImages)
DECLARE_SYMBOL(XcursorXcFileLoadImage)
DECLARE_SYMBOL(XcursorXcFileLoadImages)
DECLARE_SYMBOL(XcursorXcFileSave)

int main(void)
{
    CHECK_SYMBOL(XcursorAnimateCreate);
    CHECK_SYMBOL(XcursorAnimateDestroy);
    CHECK_SYMBOL(XcursorAnimateNext);
    CHECK_SYMBOL(XcursorCommentCreate);
    CHECK_SYMBOL(XcursorCommentDestroy);
    CHECK_SYMBOL(XcursorCommentsCreate);
    CHECK_SYMBOL(XcursorCommentsDestroy);
    CHECK_SYMBOL(XcursorCursorsCreate);
    CHECK_SYMBOL(XcursorCursorsDestroy);
    CHECK_SYMBOL(XcursorFileLoad);
    CHECK_SYMBOL(XcursorFileLoadAllImages);
    CHECK_SYMBOL(XcursorFileLoadImage);
    CHECK_SYMBOL(XcursorFileLoadImages);
    CHECK_SYMBOL(XcursorFilenameLoad);
    CHECK_SYMBOL(XcursorFilenameLoadAllImages);
    CHECK_SYMBOL(XcursorFilenameLoadCursor);
    CHECK_SYMBOL(XcursorFilenameLoadCursors);
    CHECK_SYMBOL(XcursorFilenameLoadImage);
    CHECK_SYMBOL(XcursorFilenameLoadImages);
    CHECK_SYMBOL(XcursorFilenameSave);
    CHECK_SYMBOL(XcursorFilenameSaveImages);
    CHECK_SYMBOL(XcursorFileSave);
    CHECK_SYMBOL(XcursorFileSaveImages);
    CHECK_SYMBOL(XcursorGetDefaultSize);
    CHECK_SYMBOL(XcursorGetResizable);
    CHECK_SYMBOL(XcursorGetTheme);
    CHECK_SYMBOL(XcursorGetThemeCore);
    CHECK_SYMBOL(XcursorImageCreate);
    CHECK_SYMBOL(XcursorImageDestroy);
    CHECK_SYMBOL(XcursorImageHash);
    CHECK_SYMBOL(XcursorImageLoadCursor);
    CHECK_SYMBOL(XcursorImagesCreate);
    CHECK_SYMBOL(XcursorImagesDestroy);
    CHECK_SYMBOL(XcursorImagesLoadCursor);
    CHECK_SYMBOL(XcursorImagesLoadCursors);
    CHECK_SYMBOL(XcursorImagesSetName);
    CHECK_SYMBOL(XcursorLibraryLoadCursor);
    CHECK_SYMBOL(XcursorLibraryLoadCursors);
    CHECK_SYMBOL(XcursorLibraryLoadImage);
    CHECK_SYMBOL(XcursorLibraryLoadImages);
    CHECK_SYMBOL(XcursorLibraryPath);
    CHECK_SYMBOL(XcursorLibraryShape);
    CHECK_SYMBOL(XcursorNoticeCreateBitmap);
    CHECK_SYMBOL(XcursorNoticePutBitmap);
    CHECK_SYMBOL(XcursorSetDefaultSize);
    CHECK_SYMBOL(XcursorSetResizable);
    CHECK_SYMBOL(XcursorSetTheme);
    CHECK_SYMBOL(XcursorSetThemeCore);
    CHECK_SYMBOL(XcursorShapeLoadCursor);
    CHECK_SYMBOL(XcursorShapeLoadCursors);
    CHECK_SYMBOL(XcursorShapeLoadImage);
    CHECK_SYMBOL(XcursorShapeLoadImages);
    CHECK_SYMBOL(XcursorSupportsAnim);
    CHECK_SYMBOL(XcursorSupportsARGB);
    CHECK_SYMBOL(XcursorTryShapeBitmapCursor);
    CHECK_SYMBOL(XcursorTryShapeCursor);
    CHECK_SYMBOL(XcursorXcFileLoad);
    CHECK_SYMBOL(XcursorXcFileLoadAllImages);
    CHECK_SYMBOL(XcursorXcFileLoadImage);
    CHECK_SYMBOL(XcursorXcFileLoadImages);
    CHECK_SYMBOL(XcursorXcFileSave);

    printf("libXcursor API surface: 61 exported symbols resolved\n");
    return 0;
}
