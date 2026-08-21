#include <stddef.h>
#include <X11/extensions/Xrender.h>

int main(void)
{
    char full_alpha[] = "rgba:f/0/8/f";
    char half_alpha[] = "rgba:ffff/8000/0000/8000";
    char zero_alpha[] = "rgba:ffff/ffff/ffff/0";
    char overlong[] = "rgba:10000/0/0/f";
    char empty[] = "rgba:/0/0/f";
    char uppercase[] = "rgba:F/0/0/f";
    XRenderColor color = {0};

    if (!XRenderParseColor(NULL, full_alpha, &color) ||
        color.red != 0xffff || color.green != 0 || color.blue != 0x8888 ||
        color.alpha != 0xffff) {
        return 1;
    }
    if (!XRenderParseColor(NULL, half_alpha, &color) ||
        color.red != 0x8000 || color.green != 0x4000 || color.blue != 0 ||
        color.alpha != 0x8000) {
        return 2;
    }
    if (!XRenderParseColor(NULL, zero_alpha, &color) || color.red != 0 ||
        color.green != 0 || color.blue != 0 || color.alpha != 0) {
        return 3;
    }
    if (XRenderParseColor(NULL, overlong, &color) ||
        XRenderParseColor(NULL, empty, &color) ||
        XRenderParseColor(NULL, uppercase, &color)) {
        return 4;
    }
    return 0;
}
