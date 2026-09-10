// kdecoration 6.7.2 consumer test (R34: exercises real KDecoration3 API).
// Verifies that the DecorationThemeMetaData value-type API from
// libkdecorations3.so works after packaging: setters and getters must
// round-trip, including the KDecoration3::BorderSize enum.
#include <KDecoration3/DecorationThemeProvider>
#include <KDecoration3/decorationdefines.h>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    KDecoration3::DecorationThemeMetaData meta;
    meta.setVisibleName(QStringLiteral("Breeze"));
    meta.setThemeName(QStringLiteral("org.kde.breeze"));
    meta.setConfigurationName(QStringLiteral("kwinrc"));
    meta.setPluginId(QStringLiteral("org.kde.breeze"));
    meta.setBorderSize(KDecoration3::BorderSize::Normal);

    if (meta.visibleName() != QStringLiteral("Breeze")) {
        std::printf("FAIL: visibleName mismatch: %s\n",
                    meta.visibleName().toUtf8().constData());
        return 1;
    }
    if (meta.themeName() != QStringLiteral("org.kde.breeze")) {
        std::printf("FAIL: themeName mismatch: %s\n",
                    meta.themeName().toUtf8().constData());
        return 1;
    }
    if (meta.configurationName() != QStringLiteral("kwinrc")) {
        std::printf("FAIL: configurationName mismatch: %s\n",
                    meta.configurationName().toUtf8().constData());
        return 1;
    }
    if (meta.pluginId() != QStringLiteral("org.kde.breeze")) {
        std::printf("FAIL: pluginId mismatch: %s\n",
                    meta.pluginId().toUtf8().constData());
        return 1;
    }
    if (meta.borderSize() != KDecoration3::BorderSize::Normal) {
        std::printf("FAIL: borderSize mismatch (expected Normal)\n");
        return 1;
    }
    std::printf("PASS: DecorationThemeMetaData round-trip ok "
                "(theme=%s borderSize=Normal)\n",
                meta.themeName().toUtf8().constData());
    return 0;
}
