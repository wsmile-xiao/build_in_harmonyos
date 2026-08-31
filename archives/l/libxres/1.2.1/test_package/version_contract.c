#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
/* XResproto.h is not self-contained: it uses CARD32 but includes nothing;
 * Xmd.h must come first. */
#include <X11/Xmd.h>
#include <X11/extensions/XResproto.h>
#include <X11/extensions/XRes.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* X-Resource protocol version constants (xorgproto XResproto.h) */
    CHECK(XRES_MAJOR_VERSION == 1, "XRES_MAJOR_VERSION == 1");
    CHECK(XRES_MINOR_VERSION == 2, "XRES_MINOR_VERSION == 2");
    CHECK(strcmp(XRES_NAME, "X-Resource") == 0, "XRES_NAME == \"X-Resource\"");

    /* X-Resource request opcodes */
    CHECK(X_XResQueryVersion == 0, "X_XResQueryVersion == 0");
    CHECK(X_XResQueryClients == 1, "X_XResQueryClients == 1");
    CHECK(X_XResQueryClientResources == 2, "X_XResQueryClientResources == 2");
    CHECK(X_XResQueryClientPixmapBytes == 3, "X_XResQueryClientPixmapBytes == 3");
    CHECK(X_XResQueryClientIds == 4, "X_XResQueryClientIds == 4");
    CHECK(X_XResQueryResourceBytes == 5, "X_XResQueryResourceBytes == 5");

    /* Client ID selectors (libXres XRes.h) */
    CHECK(XRES_CLIENT_ID_XID == 0, "XRES_CLIENT_ID_XID == 0");
    CHECK(XRES_CLIENT_ID_PID == 1, "XRES_CLIENT_ID_PID == 1");
    CHECK(XRES_CLIENT_ID_NR == 2, "XRES_CLIENT_ID_NR == 2");
    CHECK(XRES_CLIENT_ID_XID_MASK == 1, "XRES_CLIENT_ID_XID_MASK == 1");
    CHECK(XRES_CLIENT_ID_PID_MASK == 2, "XRES_CLIENT_ID_PID_MASK == 2");

    /* ABI surface: key types are usable and complete */
    CHECK(sizeof(XResClient) > 0, "XResClient usable");
    CHECK(sizeof(XResType) > 0, "XResType usable");
    CHECK(sizeof(XResClientIdValue) > 0, "XResClientIdValue usable");
    CHECK(sizeof(XResResourceSizeValue) > 0, "XResResourceSizeValue usable");
    CHECK(sizeof(XID) > 0, "XID usable");

    printf("libXres version contract: all checks passed\n");
    return 0;
}
