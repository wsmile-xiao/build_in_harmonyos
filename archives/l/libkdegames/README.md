# libkdegames

libkdegames is the shared library used by KDE games. It provides the
KGameRenderer SVG theming engine (KGameRenderer/KGameRendererClient/
KGameRenderedItem), theme description handling (KGameTheme/
KGameThemeProvider/KGameThemeSelector), the highscore framework
(KGameHighscore/KGameHighScoreDialog), KGameClock, KGameDifficulty,
KGamePopupItem scene messages, the OpenAL-backed KGameAudioScene/KGameSound,
the KDEGamesPrivate network/message layer (KGame/KPlayer/KMessageIO/KChatBase)
and the org.kde.games.core QML module plus the shared carddecks SVG decks.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KF_SKIP_PO_PROCESSING=ON` skips the `ki18n_install(po)` catalog step; the
  library does not need translated catalogs to build or link.
- The KF6 dependency closure is the upstream 26.04.0 set (Archive,
  ColorScheme, Completion, Config, ConfigWidgets, DNSSD, GuiAddons,
  IconThemes, I18n, NewStuff, XmlGui) resolved from the ohpcd registry at
  6.18.0 (kdnssd 6.29.0). `karchive/6.18.0` is pinned with `override=True`
  because the newest `kiconthemes/6.18.0` recipe revision requires
  `karchive/6.19.0` while `knewstuff/6.18.0` requires `karchive/6.18.0`;
  the override keeps the whole graph on one karchive version.
- OpenAL (`openal-soft/1.25.2`) and libsndfile (`libsndfile/1.2.2`) are
  found through their upstream CMake config files once the conan package
  `lib/cmake` dirs are prepended to `CMAKE_PREFIX_PATH`. The configure-time
  `try_compile` capability check for libsndfile (Ogg/Vorbis enums) passes
  against the conan package.
- `svgcleaner` and `7Zip` are optional; the carddecks SVGZ generation falls
  back to `gzip -9 -n -c` and skips SVG cleaning (`BUILD_SVG_CHECKS=OFF` is
  the upstream default).
- Upstream CTest suite runs inside `conan create` with the offscreen Qt
  platform and a sandboxed XDG/HOME/TMPDIR tree.

## Products

- `libKDEGames6.so` (target `KDEGames6`, cmake package `KDEGames6`)
- `libKDEGames6Private.so` (target `KDEGames6Private`)
- `org.kde.games.core` QML module (`corebindingsplugin`)
- shared carddecks SVGZ decks and qlogging categories
