// kcolorscheme 6.18.0.1 consumer test (R34: exercises real API).
// Constructs a KColorScheme and verifies basic accessor behavior.
#include <KColorScheme>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KColorScheme scheme(QPalette::Active, KColorScheme::View);
    const QBrush bg = scheme.background(KColorScheme::NormalBackground);
    // background() must return a valid brush for the View group.
    if (!bg.color().isValid()) {
        std::printf("FAIL: background color invalid\n");
        return 1;
    }
    std::printf("PASS: KColorScheme background OK (rgb %d,%d,%d)\n",
                bg.color().red(), bg.color().green(), bg.color().blue());
    return 0;
}
