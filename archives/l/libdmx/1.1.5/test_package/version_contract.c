#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
/* dmxproto.h is not self-contained: it uses CARD32 but includes nothing;
 * Xmd.h must come first. */
#include <X11/Xmd.h>
#include <X11/extensions/dmxproto.h>
#include <X11/extensions/dmx.h>
#include <X11/extensions/dmxext.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* DMX protocol version constants (xorgproto dmxproto.h) */
    CHECK(strcmp(DMX_EXTENSION_NAME, "DMX") == 0,
          "DMX_EXTENSION_NAME == \"DMX\"");
    CHECK(DMX_EXTENSION_MAJOR == 2, "DMX_EXTENSION_MAJOR == 2");
    CHECK(DMX_EXTENSION_MINOR == 2, "DMX_EXTENSION_MINOR == 2");
    CHECK(DMX_EXTENSION_PATCH == 20040604,
          "DMX_EXTENSION_PATCH == 20040604");

    /* DMX request opcodes (xorgproto dmxproto.h) */
    CHECK(X_DMXQueryVersion == 0, "X_DMXQueryVersion == 0");
    CHECK(X_DMXGetScreenCount == 1, "X_DMXGetScreenCount == 1");
    CHECK(X_DMXGetWindowAttributes == 3, "X_DMXGetWindowAttributes == 3");
    CHECK(X_DMXGetInputCount == 4, "X_DMXGetInputCount == 4");
    CHECK(X_DMXGetInputAttributes == 5, "X_DMXGetInputAttributes == 5");
    CHECK(X_DMXSync == 8, "X_DMXSync == 8");
    CHECK(X_DMXForceWindowCreation == 9, "X_DMXForceWindowCreation == 9");
    CHECK(X_DMXGetScreenAttributes == 10, "X_DMXGetScreenAttributes == 10");
    CHECK(X_DMXChangeScreensAttributes == 11,
          "X_DMXChangeScreensAttributes == 11");
    CHECK(X_DMXAddScreen == 12, "X_DMXAddScreen == 12");
    CHECK(X_DMXRemoveScreen == 13, "X_DMXRemoveScreen == 13");
    CHECK(X_DMXGetDesktopAttributes == 14,
          "X_DMXGetDesktopAttributes == 14");
    CHECK(X_DMXChangeDesktopAttributes == 15,
          "X_DMXChangeDesktopAttributes == 15");
    CHECK(X_DMXAddInput == 16, "X_DMXAddInput == 16");
    CHECK(X_DMXRemoveInput == 17, "X_DMXRemoveInput == 17");

    /* Wire sizes for the fixed-size requests the library sends */
    CHECK(sz_xDMXQueryVersionReq == 4, "sz_xDMXQueryVersionReq == 4");
    CHECK(sz_xDMXGetScreenCountReq == 4, "sz_xDMXGetScreenCountReq == 4");
    CHECK(sz_xDMXSyncReq == 4, "sz_xDMXSyncReq == 4");
    CHECK(sz_xDMXGetScreenCountReply == 32,
          "sz_xDMXGetScreenCountReply == 32");
    CHECK(sz_xDMXQueryVersionReply == 32,
          "sz_xDMXQueryVersionReply == 32");

    /* DMX extension error codes (dmx.h must match dmxproto.h) */
    CHECK(DmxBadXinerama == DMX_BAD_XINERAMA, "DmxBadXinerama == 1001");
    CHECK(DmxBadValue == DMX_BAD_VALUE, "DmxBadValue == 1002");
    CHECK(DmxBadReply == 1003, "DmxBadReply == 1003");

    /* Attribute-selection masks (dmx.h) */
    CHECK(DMXScreenWindowWidth == (1L << 0), "DMXScreenWindowWidth == 0x1");
    CHECK(DMXRootWindowWidth == (1L << 4), "DMXRootWindowWidth == 0x10");
    CHECK(DMXRootWindowYorigin == (1L << 9),
          "DMXRootWindowYorigin == 0x200");
    CHECK(DMXDesktopWidth == (1L << 0), "DMXDesktopWidth == 0x1");
    CHECK(DMXDesktopShiftY == (1L << 3), "DMXDesktopShiftY == 0x8");
    CHECK(DMXInputType == (1L << 0), "DMXInputType == 0x1");
    CHECK(DMXInputPhysicalScreen == (1L << 1),
          "DMXInputPhysicalScreen == 0x2");
    CHECK(DMXInputSendsCore == (1L << 2), "DMXInputSendsCore == 0x4");

    /* ABI surface: key types are usable and complete */
    CHECK(sizeof(DMXScreenAttributes) > 0, "DMXScreenAttributes usable");
    CHECK(sizeof(DMXWindowAttributes) > 0, "DMXWindowAttributes usable");
    CHECK(sizeof(DMXDesktopAttributes) > 0, "DMXDesktopAttributes usable");
    CHECK(sizeof(DMXInputAttributes) > 0, "DMXInputAttributes usable");
    CHECK(DMXLocalInputType == 0, "DMXLocalInputType == 0");
    CHECK(DMXConsoleInputType == 1, "DMXConsoleInputType == 1");
    CHECK(DMXBackendInputType == 2, "DMXBackendInputType == 2");

    /* Struct layout oracles: field offsets pinned by wire consumers */
    {
        DMXDesktopAttributes desktop;
        memset(&desktop, 0, sizeof(desktop));
        desktop.width = 1600;
        desktop.height = 1200;
        desktop.shiftX = -8;
        desktop.shiftY = 16;
        CHECK(desktop.width == 1600 && desktop.height == 1200 &&
                  desktop.shiftX == -8 && desktop.shiftY == 16,
              "DMXDesktopAttributes field round-trip");
    }
    {
        DMXInputAttributes input;
        memset(&input, 0, sizeof(input));
        input.inputType = DMXBackendInputType;
        input.physicalScreen = 3;
        input.isCore = False;
        input.sendsCore = True;
        input.name = "console";
        input.detached = False;
        CHECK(input.inputType == DMXBackendInputType &&
                  input.physicalScreen == 3 && input.isCore == False &&
                  input.sendsCore == True && input.detached == False,
              "DMXInputAttributes field round-trip");
    }

    printf("libdmx version contract: all checks passed\n");
    return 0;
}
