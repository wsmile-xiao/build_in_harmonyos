/*
 * libXpm.so.4 API surface probe.
 *
 * Every Xpm* symbol exported by libXpm.so.4 is taken by address through a
 * strongly-typed live relocation, so a missing implementation or a signature
 * mismatch fails at link/load time instead of being silently dropped.
 * The test needs no X server: taking the address only requires the header.
 */

#include <stdio.h>
#include <X11/xpm.h>

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

DECLARE_SYMBOL(XpmAttributesSize)
DECLARE_SYMBOL(XpmCreateBufferFromImage)
DECLARE_SYMBOL(XpmCreateBufferFromPixmap)
DECLARE_SYMBOL(XpmCreateBufferFromXpmImage)
DECLARE_SYMBOL(XpmCreateDataFromImage)
DECLARE_SYMBOL(XpmCreateDataFromPixmap)
DECLARE_SYMBOL(XpmCreateDataFromXpmImage)
DECLARE_SYMBOL(XpmCreateImageFromBuffer)
DECLARE_SYMBOL(XpmCreateImageFromData)
DECLARE_SYMBOL(XpmCreateImageFromXpmImage)
DECLARE_SYMBOL(XpmCreatePixmapFromBuffer)
DECLARE_SYMBOL(XpmCreatePixmapFromData)
DECLARE_SYMBOL(XpmCreatePixmapFromXpmImage)
DECLARE_SYMBOL(XpmCreateXpmImageFromBuffer)
DECLARE_SYMBOL(XpmCreateXpmImageFromData)
DECLARE_SYMBOL(XpmCreateXpmImageFromImage)
DECLARE_SYMBOL(XpmCreateXpmImageFromPixmap)
DECLARE_SYMBOL(XpmFree)
DECLARE_SYMBOL(XpmFreeAttributes)
DECLARE_SYMBOL(XpmFreeExtensions)
DECLARE_SYMBOL(XpmFreeXpmImage)
DECLARE_SYMBOL(XpmFreeXpmInfo)
DECLARE_SYMBOL(XpmGetErrorString)
DECLARE_SYMBOL(XpmLibraryVersion)
DECLARE_SYMBOL(XpmReadFileToBuffer)
DECLARE_SYMBOL(XpmReadFileToData)
DECLARE_SYMBOL(XpmReadFileToImage)
DECLARE_SYMBOL(XpmReadFileToPixmap)
DECLARE_SYMBOL(XpmReadFileToXpmImage)
DECLARE_SYMBOL(XpmWriteFileFromBuffer)
DECLARE_SYMBOL(XpmWriteFileFromData)
DECLARE_SYMBOL(XpmWriteFileFromImage)
DECLARE_SYMBOL(XpmWriteFileFromPixmap)
DECLARE_SYMBOL(XpmWriteFileFromXpmImage)

int main(void)
{
    CHECK_SYMBOL(XpmAttributesSize);
    CHECK_SYMBOL(XpmCreateBufferFromImage);
    CHECK_SYMBOL(XpmCreateBufferFromPixmap);
    CHECK_SYMBOL(XpmCreateBufferFromXpmImage);
    CHECK_SYMBOL(XpmCreateDataFromImage);
    CHECK_SYMBOL(XpmCreateDataFromPixmap);
    CHECK_SYMBOL(XpmCreateDataFromXpmImage);
    CHECK_SYMBOL(XpmCreateImageFromBuffer);
    CHECK_SYMBOL(XpmCreateImageFromData);
    CHECK_SYMBOL(XpmCreateImageFromXpmImage);
    CHECK_SYMBOL(XpmCreatePixmapFromBuffer);
    CHECK_SYMBOL(XpmCreatePixmapFromData);
    CHECK_SYMBOL(XpmCreatePixmapFromXpmImage);
    CHECK_SYMBOL(XpmCreateXpmImageFromBuffer);
    CHECK_SYMBOL(XpmCreateXpmImageFromData);
    CHECK_SYMBOL(XpmCreateXpmImageFromImage);
    CHECK_SYMBOL(XpmCreateXpmImageFromPixmap);
    CHECK_SYMBOL(XpmFree);
    CHECK_SYMBOL(XpmFreeAttributes);
    CHECK_SYMBOL(XpmFreeExtensions);
    CHECK_SYMBOL(XpmFreeXpmImage);
    CHECK_SYMBOL(XpmFreeXpmInfo);
    CHECK_SYMBOL(XpmGetErrorString);
    CHECK_SYMBOL(XpmLibraryVersion);
    CHECK_SYMBOL(XpmReadFileToBuffer);
    CHECK_SYMBOL(XpmReadFileToData);
    CHECK_SYMBOL(XpmReadFileToImage);
    CHECK_SYMBOL(XpmReadFileToPixmap);
    CHECK_SYMBOL(XpmReadFileToXpmImage);
    CHECK_SYMBOL(XpmWriteFileFromBuffer);
    CHECK_SYMBOL(XpmWriteFileFromData);
    CHECK_SYMBOL(XpmWriteFileFromImage);
    CHECK_SYMBOL(XpmWriteFileFromPixmap);
    CHECK_SYMBOL(XpmWriteFileFromXpmImage);
    printf("libXpm api surface: all 34 symbols resolved\n");
    return 0;
}
