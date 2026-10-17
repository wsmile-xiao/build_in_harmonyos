#include <gdesktop-enums.h>
#include <stdio.h>

int main(void) {
    /* Verify the header is accessible and enums are defined correctly */
    GDesktopClockFormat fmt = G_DESKTOP_CLOCK_FORMAT_24H;
    GDesktopColorScheme scheme = G_DESKTOP_COLOR_SCHEME_PREFER_DARK;
    GDesktopBackgroundStyle style = G_DESKTOP_BACKGROUND_STYLE_WALLPAPER;

    if (fmt == G_DESKTOP_CLOCK_FORMAT_24H &&
        scheme == G_DESKTOP_COLOR_SCHEME_PREFER_DARK &&
        style == G_DESKTOP_BACKGROUND_STYLE_WALLPAPER) {
        printf("gsettings-desktop-schemas 49.1: header test OK\n");
        return 0;
    }
    fprintf(stderr, "Enum value mismatch\n");
    return 1;
}
