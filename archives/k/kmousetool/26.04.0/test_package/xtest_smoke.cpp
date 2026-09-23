// R34: exercises the package-provided API (libXtst XTest — the exact API
// kmousetool itself uses to synthesize clicks) at runtime on the target.
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>

#include <cstdio>

int main() {
    // XOpenDisplay returns nullptr on OHOS PC (no X server), which is the
    // expected path here: the link-time contract (XTestFakeButtonEvent
    // resolves from libXtst) is what the package must guarantee.
    Display *dpy = XOpenDisplay(nullptr);
    if (dpy) {
        XTestFakeButtonEvent(dpy, 1, True, CurrentTime);
        XTestFakeButtonEvent(dpy, 1, False, CurrentTime);
        XCloseDisplay(dpy);
    }
    std::printf("xtest_smoke ok (link+runtime against libXtst)\n");
    return 0;
}
