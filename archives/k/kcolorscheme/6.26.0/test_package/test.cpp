#include <KColorScheme>

#include <QGuiApplication>

#include <cstdio>

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    const KColorScheme scheme(QPalette::Active, KColorScheme::View);

    const auto background = scheme.background(KColorScheme::NormalBackground);
    if (!background.color().isValid()) {
        std::fprintf(stderr, "FAIL: invalid normal background color\n");
        return 1;
    }

    const auto foreground = scheme.foreground(KColorScheme::NormalText);
    if (!foreground.color().isValid()) {
        std::fprintf(stderr, "FAIL: invalid normal foreground color\n");
        return 2;
    }

    const auto decoration = scheme.decoration(KColorScheme::FocusColor);
    if (!decoration.color().isValid()) {
        std::fprintf(stderr, "FAIL: invalid focus decoration color\n");
        return 3;
    }

    const qreal contrast = KColorScheme::contrastF();
    if (contrast < 0.0 || contrast > 1.0) {
        std::fprintf(stderr, "FAIL: contrast outside [0, 1]: %.3f\n", contrast);
        return 4;
    }

    std::printf(
        "PASS: KColorScheme colors valid, contrast=%.3f, background=%s\n",
        contrast,
        background.color().name().toUtf8().constData()
    );
    return 0;
}
