#include <X11/Xlib.h>
#include <X11/Xproto.h>
#include <X11/extensions/Xext.h>
#include <X11/extensions/extutil.h>

#include <stdio.h>

static int test_handler(Display *display, const char *name, const char *reason)
{
    (void)display;
    (void)name;
    (void)reason;
    return 17;
}

int main(void)
{
    XExtensionInfo *extension = XextCreateExtension();
    XextErrorHandler previous;
    XextErrorHandler replaced;

    if (extension == NULL) {
        return 1;
    }
    XextDestroyExtension(extension);

    previous = XSetExtensionErrorHandler(test_handler);
    replaced = XSetExtensionErrorHandler(previous);
    if (replaced != test_handler) {
        return 2;
    }
    puts("LIBXEXT_TEST registry_contract PASS");
    return 0;
}
