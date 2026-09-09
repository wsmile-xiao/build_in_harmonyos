#include <KColorUtils>

#include <QColor>
#include <cstdio>

int main()
{
    // Consumer-side smoke: exercise pure color math that only needs Qt6::Gui
    const QColor base(0x2a, 0x82, 0xda);
    const QColor lighter = KColorUtils::lighten(base, 0.1);
    const QColor darker = KColorUtils::darken(base, 0.1);
    const qreal contrast = KColorUtils::luma(base);

    if (!lighter.isValid() || !darker.isValid()) {
        std::fprintf(stderr, "FAIL: lighten/darken returned invalid colors\n");
        return 1;
    }
    if (lighter.lightness() <= base.lightness()) {
        std::fprintf(stderr, "FAIL: lighten did not increase lightness\n");
        return 1;
    }
    if (darker.lightness() >= base.lightness()) {
        std::fprintf(stderr, "FAIL: darken did not decrease lightness\n");
        return 1;
    }
    if (contrast < 0.0 || contrast > 1.0) {
        std::fprintf(stderr, "FAIL: luma out of range\n");
        return 1;
    }
    std::printf("kguiaddons test_package: all assertions passed\n");
    return 0;
}
