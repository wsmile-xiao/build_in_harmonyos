// kguiaddons 6.14.0 consumer test (R34: exercises real API).
// Uses KColorUtils::mix, a pure function, to verify linking and ABI.
#include <KColorUtils>
#include <QColor>
#include <cstdio>

int main() {
    const QColor a(255, 0, 0, 255);
    const QColor b(0, 0, 255, 255);
    const QColor m = KColorUtils::mix(a, b, 0.5);
    // mix(red, blue, 0.5) -> (127/128, 0, 127/128, 255)
    if (m.blue() < 120 || m.red() < 120) {
        std::printf("FAIL: KColorUtils::mix unexpected result (%d,%d,%d)\n",
                    m.red(), m.green(), m.blue());
        return 1;
    }
    std::printf("PASS: KColorUtils::mix OK (%d,%d,%d)\n",
                m.red(), m.green(), m.blue());
    return 0;
}
