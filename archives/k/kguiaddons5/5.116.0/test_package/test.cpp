// Consumer smoke test for kguiaddons5 5.116.0 on HarmonyOS PC.
// Mirrors the API assertions of the upstream kcolorutilstest.cpp
// (testOverlay/testMix/testContrast) against the real KColorUtils API.
#include <QColor>
#include <QtGlobal>
#include <cstdio>

#include <KColorUtils>

static int failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,   \
                         #cond);                                           \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main() {
    // Upstream testOverlay: blending an opaque color leaves it unchanged.
    QColor color1(10, 10, 100);
    QColor color2(10, 10, 160);
    QColor blended = KColorUtils::overlayColors(color1, color2);
    CHECK(blended == color2);

    // Contrast ratio of black vs white is exactly 21.0 (WCAG).
    CHECK(KColorUtils::contrastRatio(Qt::black, Qt::white) == qreal(21.0));
    CHECK(KColorUtils::contrastRatio(Qt::black, Qt::black) == qreal(1.0));

    // Upstream testMix: low-opacity colorA has little influence on colorB.
    const QColor colorA = QColor::fromRgb(255, 255, 255, 1);
    const QColor colorB = QColor::fromRgb(0, 0, 0, 255);
    const QColor mixed = KColorUtils::mix(colorA, colorB, 0.5);
    CHECK(mixed.redF() <= 0.01);
    CHECK(mixed.greenF() <= 0.01);
    CHECK(mixed.blueF() <= 0.01);

    if (failures != 0) {
        std::printf("test_kguiaddons5: %d check(s) FAILED\n", failures);
        return 1;
    }
    std::printf("test_kguiaddons5 5.116.0: all checks PASSED\n");
    return 0;
}
