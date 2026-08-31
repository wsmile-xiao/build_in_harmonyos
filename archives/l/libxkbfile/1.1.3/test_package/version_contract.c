#include <stddef.h>
#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/XKBstr.h>
#include <X11/extensions/XKBfile.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

/* Compile-time signature contracts via typed function-pointer assignment:
 * under -Werror a signature change fails to compile, unlike a sizeof()
 * comparison between function-pointer types which is always true. */
static char *(*const sig_XkbKeysymText)(KeySym, unsigned) = XkbKeysymText;
static char *(*const sig_XkbKeyNameText)(char *, unsigned) = XkbKeyNameText;
static char *(*const sig_XkbAtomText)(Display *, Atom, unsigned) = XkbAtomText;

int main(void) {
    (void)sig_XkbKeysymText;
    (void)sig_XkbKeyNameText;
    (void)sig_XkbAtomText;

    /* File-type constants from XKBfile.h */
    CHECK(XkbXKMFile == 0, "XkbXKMFile == 0");
    CHECK(XkbCFile == 1, "XkbCFile == 1");
    CHECK(XkbXKBFile == 2, "XkbXKBFile == 2");
    CHECK(XkbMessage == 3, "XkbMessage == 3");

    /* Defined-bit masks */
    CHECK(XkbMapDefined == (1 << 0), "XkbMapDefined == (1<<0)");
    CHECK(XkbStateDefined == (1 << 1), "XkbStateDefined == (1<<1)");

    /* XkbFileInfo ABI layout: type, defined, xkb.
     * The size is NOT 3*sizeof(unsigned): on aarch64 the trailing XkbDescPtr
     * is an 8-byte pointer, so the struct is 16 bytes. Express the size in
     * terms of offsetof + the pointer type so the check is ABI-correct. */
    CHECK(offsetof(XkbFileInfo, type) == 0, "XkbFileInfo.type at offset 0");
    CHECK(offsetof(XkbFileInfo, defined) == sizeof(unsigned),
          "XkbFileInfo.defined after type");
    CHECK(offsetof(XkbFileInfo, xkb) == 2 * sizeof(unsigned),
          "XkbFileInfo.xkb after defined");
    CHECK(sizeof(XkbFileInfo) == offsetof(XkbFileInfo, xkb) + sizeof(XkbDescPtr),
          "XkbFileInfo size = 2*unsigned + XkbDescPtr");
    CHECK(sizeof(XkbDescPtr) == sizeof(void *),
          "XkbDescPtr is a void*-sized pointer");

    printf("libxkbfile version contract: all checks passed\n");
    return 0;
}
