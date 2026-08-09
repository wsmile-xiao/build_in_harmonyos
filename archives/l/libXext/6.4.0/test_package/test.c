/* libxext/6.4.0 consumer link + API smoke test.
 *
 * This test deliberately avoids XOpenDisplay() so it can run on a headless
 * OHOS CI worker. It still resolves and executes libXext symbols.
 */

#include <stdio.h>
#include <string.h>

#include <X11/Xlib.h>
#include <X11/Xproto.h>
#include <X11/extensions/Xext.h>
#include <X11/extensions/extutil.h>
#include <X11/extensions/shape.h>
#include <X11/extensions/shapeconst.h>

static int missing_calls = 0;

static int test_error_handler(Display *display, const char *ext_name,
                              const char *reason) {
    (void)display;
    if (ext_name == NULL || strcmp(ext_name, SHAPENAME) != 0) {
        return 1;
    }
    if (reason == NULL || strcmp(reason, X_EXTENSION_MISSING) != 0) {
        return 2;
    }
    missing_calls++;
    return 42;
}

int main(void) {
    XExtensionInfo *info = XextCreateExtension();
    if (info == NULL) {
        fprintf(stderr, "XextCreateExtension returned NULL\n");
        return 1;
    }
    if (info->head != NULL || info->cur != NULL || info->ndisplays != 0) {
        fprintf(stderr, "new XExtensionInfo is not empty\n");
        XextDestroyExtension(info);
        return 2;
    }
    if (XextFindDisplay(info, NULL) != NULL) {
        fprintf(stderr, "unexpected NULL display match\n");
        XextDestroyExtension(info);
        return 3;
    }

    XextErrorHandler old_handler = XSetExtensionErrorHandler(test_error_handler);
    int rc = XMissingExtension(NULL, SHAPENAME);
    XSetExtensionErrorHandler(old_handler);
    XextDestroyExtension(info);

    if (rc != 42) {
        fprintf(stderr, "XMissingExtension returned %d\n", rc);
        return 4;
    }
    if (missing_calls != 1) {
        fprintf(stderr, "handler call count = %d\n", missing_calls);
        return 5;
    }
    if (ShapeNotify != 0 || ShapeNumberEvents < 1) {
        fprintf(stderr, "unexpected Shape constants\n");
        return 6;
    }

    printf("libxext api smoke ok\n");
    return 0;
}
