#include <stdio.h>
#include <X11/Xlib.h>
#include <X11/extensions/saver.h>
#include <X11/extensions/scrnsaver.h>

int main(void) {
    XScreenSaverInfo *info = XScreenSaverAllocInfo();
    if (info == NULL) {
        return 1;
    }

    info->window = (Window)0x1234;
    info->state = ScreenSaverOff;
    info->kind = ScreenSaverBlanked;
    info->idle = 42;
    info->eventMask = ScreenSaverNotifyMask;

    if (info->window != (Window)0x1234 ||
        info->state != ScreenSaverOff ||
        info->kind != ScreenSaverBlanked ||
        info->idle != 42 ||
        info->eventMask != ScreenSaverNotifyMask) {
        XFree(info);
        return 2;
    }

    XFree(info);
    puts("libxscrnsaver API smoke passed");
    return 0;
}
