// Consumer test: exercise exported KDecoration3 value-type API after packaging.
#include <KDecoration3/DecorationThemeProvider>
#include <QCoreApplication>
#include <QString>
#include <kdecoration3/decorationdefines.h>

#include <cstdio>

int main(int argc, char **argv) {
  QCoreApplication app(argc, argv);

  KDecoration3::DecorationThemeMetaData metadata;
  metadata.setVisibleName(QStringLiteral("Breeze"));
  metadata.setThemeName(QStringLiteral("org.kde.breeze"));
  metadata.setConfigurationName(QStringLiteral("kwinrc"));
  metadata.setPluginId(QStringLiteral("org.kde.breeze"));
  metadata.setBorderSize(KDecoration3::BorderSize::Normal);

  if (metadata.visibleName() != QStringLiteral("Breeze")) {
    std::fprintf(stderr, "visibleName round-trip failed\n");
    return 1;
  }
  if (metadata.themeName() != QStringLiteral("org.kde.breeze")) {
    std::fprintf(stderr, "themeName round-trip failed\n");
    return 2;
  }
  if (metadata.configurationName() != QStringLiteral("kwinrc")) {
    std::fprintf(stderr, "configurationName round-trip failed\n");
    return 3;
  }
  if (metadata.pluginId() != QStringLiteral("org.kde.breeze")) {
    std::fprintf(stderr, "pluginId round-trip failed\n");
    return 4;
  }
  if (metadata.borderSize() != KDecoration3::BorderSize::Normal) {
    std::fprintf(stderr, "borderSize round-trip failed\n");
    return 5;
  }

  std::printf("KDecoration3 consumer API test passed\n");
  return 0;
}
