#include <stdio.h>

#include <X11/XKBlib.h>
#include <X11/Xlib-xcb.h>
#include <X11/Xlib.h>
#include <X11/Xresource.h>
#include <X11/Xutil.h>

static xcb_connection_t *(*volatile require_xgetxcbconnection)(Display *) =
    XGetXCBConnection;

static int test_error_handler(Display *display, XErrorEvent *event)
{
    (void)display;
    (void)event;
    return 0;
}

int main(void)
{
    if (!XInitThreads()) {
        fprintf(stderr, "XInitThreads failed\n");
        return 1;
    }

    XrmInitialize();
    XrmQuark quark = XrmStringToQuark("libx11.test.resource");
    if (quark == NULLQUARK) {
        fprintf(stderr, "XrmStringToQuark returned NULLQUARK\n");
        return 2;
    }

    KeySym keysym = XStringToKeysym("A");
    if (keysym == NoSymbol || XKeysymToString(keysym) == NULL) {
        fprintf(stderr, "keysym round-trip failed\n");
        return 3;
    }

    int (*old_handler)(Display *, XErrorEvent *) = XSetErrorHandler(test_error_handler);
    XSetErrorHandler(old_handler);

    (void)require_xgetxcbconnection;

    printf("libx11 consumer smoke passed: quark=%lu keysym=%lu\n",
           (unsigned long)quark, (unsigned long)keysym);
    return 0;
}
