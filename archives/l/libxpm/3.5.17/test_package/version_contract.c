/*
 * libXpm ABI contract + functional smoke test.
 *
 * Part 1 pins the version macros, the public struct layouts (offsetof-based,
 * so the checks stay correct on both 32- and 64-bit targets), and exported
 * function signatures via typed function-pointer assignment (a real
 * compile-time check under -Werror, not a runtime sizeof() no-op).
 *
 * Part 2 is a display-independent round-trip: parse a tiny inline XPM array
 * into an XpmImage, write it to a file, read it back, and regenerate the
 * XPM data array.  None of these code paths touch an X server.
 */

#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <X11/xpm.h>

static int checks = 0;
#define CHECK(cond, msg)                                     \
    do {                                                     \
        checks++;                                            \
        if (!(cond)) {                                       \
            fprintf(stderr, "FAIL: %s\n", msg);              \
            return 1;                                        \
        }                                                    \
    } while (0)

/* --- compile-time signature contracts (typed assignment) --- */
static int (*const sig_XpmAttributesSize)(void) = XpmAttributesSize;
static int (*const sig_XpmLibraryVersion)(void) = XpmLibraryVersion;
static char *(*const sig_XpmGetErrorString)(int) = XpmGetErrorString;
static void (*const sig_XpmFree)(void *) = XpmFree;
static void (*const sig_XpmFreeAttributes)(XpmAttributes *) = XpmFreeAttributes;
static void (*const sig_XpmFreeExtensions)(XpmExtension *, int) = XpmFreeExtensions;
static void (*const sig_XpmFreeXpmImage)(XpmImage *) = XpmFreeXpmImage;
static void (*const sig_XpmFreeXpmInfo)(XpmInfo *) = XpmFreeXpmInfo;
static int (*const sig_XpmReadFileToXpmImage)(const char *, XpmImage *, XpmInfo *) =
    XpmReadFileToXpmImage;
static int (*const sig_XpmWriteFileFromXpmImage)(const char *, XpmImage *, XpmInfo *) =
    XpmWriteFileFromXpmImage;
static int (*const sig_XpmCreateXpmImageFromData)(char **, XpmImage *, XpmInfo *) =
    XpmCreateXpmImageFromData;
static int (*const sig_XpmCreateXpmImageFromBuffer)(char *, XpmImage *, XpmInfo *) =
    XpmCreateXpmImageFromBuffer;
static int (*const sig_XpmCreateDataFromXpmImage)(char ***, XpmImage *, XpmInfo *) =
    XpmCreateDataFromXpmImage;
static int (*const sig_XpmCreateBufferFromXpmImage)(char **, XpmImage *, XpmInfo *) =
    XpmCreateBufferFromXpmImage;
static int (*const sig_XpmReadFileToBuffer)(const char *, char **) = XpmReadFileToBuffer;
static int (*const sig_XpmWriteFileFromBuffer)(const char *, char *) = XpmWriteFileFromBuffer;
static int (*const sig_XpmReadFileToData)(const char *, char ***) = XpmReadFileToData;
static int (*const sig_XpmWriteFileFromData)(const char *, char **) = XpmWriteFileFromData;

int main(void)
{
    (void)sig_XpmAttributesSize;
    (void)sig_XpmLibraryVersion;
    (void)sig_XpmGetErrorString;
    (void)sig_XpmFree;
    (void)sig_XpmFreeAttributes;
    (void)sig_XpmFreeExtensions;
    (void)sig_XpmFreeXpmImage;
    (void)sig_XpmFreeXpmInfo;
    (void)sig_XpmReadFileToXpmImage;
    (void)sig_XpmWriteFileFromXpmImage;
    (void)sig_XpmCreateXpmImageFromData;
    (void)sig_XpmCreateXpmImageFromBuffer;
    (void)sig_XpmCreateDataFromXpmImage;
    (void)sig_XpmCreateBufferFromXpmImage;
    (void)sig_XpmReadFileToBuffer;
    (void)sig_XpmWriteFileFromBuffer;
    (void)sig_XpmReadFileToData;
    (void)sig_XpmWriteFileFromData;

    /* --- version contract --- */
    CHECK(XpmFormat == 3, "XpmFormat == 3");
    CHECK(XpmVersion == 4, "XpmVersion == 4");
    CHECK(XpmRevision == 11, "XpmRevision == 11");
    CHECK(XpmIncludeVersion == 30411, "XpmIncludeVersion == 30411");

    /* --- scalar ABI types --- */
    CHECK(sizeof(unsigned int) == 4, "unsigned int is 4 bytes");
    CHECK(sizeof(Pixel) == sizeof(unsigned long), "Pixel is unsigned long");

    /* --- XpmColor: 6 char* members --- */
    CHECK(sizeof(XpmColor) == 6 * sizeof(char *), "XpmColor is 6 pointers");
    CHECK(offsetof(XpmColor, symbolic) == sizeof(char *), "XpmColor.symbolic offset");
    CHECK(offsetof(XpmColor, m_color) == 2 * sizeof(char *), "XpmColor.m_color offset");
    CHECK(offsetof(XpmColor, c_color) == 5 * sizeof(char *), "XpmColor.c_color offset");

    /* --- XpmColorSymbol: name, value, Pixel --- */
    CHECK(sizeof(XpmColorSymbol) == 3 * sizeof(void *),
          "XpmColorSymbol is 2 pointers + Pixel");
    CHECK(offsetof(XpmColorSymbol, pixel) == 2 * sizeof(char *),
          "XpmColorSymbol.pixel offset");

    /* --- XpmImage: 4 uints then two trailing pointers --- */
    CHECK(offsetof(XpmImage, colorTable) == 4 * sizeof(unsigned int),
          "XpmImage.colorTable offset");
    CHECK(sizeof(XpmImage) == offsetof(XpmImage, data) + sizeof(unsigned int *),
          "XpmImage size (data last, pointer-aligned)");

    /* --- XpmExtension: name ptr, nlines uint, lines ptr --- */
    CHECK(offsetof(XpmExtension, lines) >=
              offsetof(XpmExtension, nlines) + sizeof(unsigned int),
          "XpmExtension.lines after nlines");
    CHECK(sizeof(XpmExtension) == offsetof(XpmExtension, lines) + sizeof(char **),
          "XpmExtension size (lines last, pointer-aligned)");

    /* --- XpmInfo: valuemask + 3 char* + 2 uints + extensions ptr --- */
    CHECK(offsetof(XpmInfo, extensions) >=
              offsetof(XpmInfo, nextensions) + sizeof(unsigned int),
          "XpmInfo.extensions after nextensions");
    CHECK(sizeof(XpmInfo) == offsetof(XpmInfo, extensions) + sizeof(XpmExtension *),
          "XpmInfo size (extensions last, pointer-aligned)");

    /* --- functional round-trip (display-independent) --- */
    {
        static char *const raw_xpm[] = {
            "1 1 1 1",
            "a c #ff0000",
            "a",
            NULL,
        };
        XpmImage image;
        XpmImage image2;
        char **data_return = NULL;
        int rc;

        fprintf(stderr, "[xpm] phase: create-from-data\n");
        rc = XpmCreateXpmImageFromData((char **)raw_xpm, &image, NULL);
        CHECK(rc == XpmSuccess, "XpmCreateXpmImageFromData succeeds");
        CHECK(image.width == 1, "parsed width == 1");
        CHECK(image.height == 1, "parsed height == 1");
        CHECK(image.cpp == 1, "parsed cpp == 1");
        CHECK(image.ncolors == 1, "parsed ncolors == 1");
        CHECK(image.colorTable != NULL, "colorTable populated");
        CHECK(image.colorTable[0].c_color != NULL, "color value parsed");
        CHECK(image.data != NULL, "pixel data populated");

        fprintf(stderr, "[xpm] phase: write-file\n");
        rc = XpmWriteFileFromXpmImage("xpm_roundtrip.xpm", &image, NULL);
        CHECK(rc == XpmSuccess, "XpmWriteFileFromXpmImage succeeds");

        fprintf(stderr, "[xpm] phase: read-file\n");
        rc = XpmReadFileToXpmImage("xpm_roundtrip.xpm", &image2, NULL);
        CHECK(rc == XpmSuccess, "XpmReadFileToXpmImage succeeds");
        CHECK(image2.width == 1, "round-tripped width == 1");
        CHECK(image2.height == 1, "round-tripped height == 1");

        fprintf(stderr, "[xpm] phase: create-data\n");
        rc = XpmCreateDataFromXpmImage(&data_return, &image, NULL);
        CHECK(rc == XpmSuccess, "XpmCreateDataFromXpmImage succeeds");
        CHECK(data_return != NULL && data_return[0] != NULL,
              "regenerated XPM data non-empty");

        fprintf(stderr, "[xpm] phase: cleanup\n");
        XpmFreeXpmImage(&image);
        XpmFreeXpmImage(&image2);
        /* XpmCreateDataFromXpmImage returns ONE malloc'd block whose rows
         * point into it (man XpmCreateData: "a single block malloc'ed
         * data").  Free it once — freeing each row would double-free. */
        if (data_return)
            XpmFree(data_return);
        remove("xpm_roundtrip.xpm");
    }

    printf("ok: libXpm version contract + round-trip (%d checks)\n", checks);
    return 0;
}
