# klevernotes 1.3.1 — OHOS port notes

## What this is

KDE note-taking app (Kirigami QML). Upstream builds its QML fully statically
(`ecm_add_qml_module(klevernotes_static URI org.kde.klevernotes
GENERATE_PLUGIN_SOURCE)`) and links `klevernotes_static` +
`klevernotes_staticplugin` into the single `klevernotes` executable.

## Partial adaptation (user-accepted, final decision 2026-09-21): WebEngine degradation

Final decision (2026-09-21): the user confirmed acceptance of all four
functional degradations of this port (WebEngine/PDF preview removal,
qqc2-desktop-style Basic-style fallback, kiconthemes QML degradation,
preview CSS degradation); the delivery form is a successful PR coexisting
with a partial-adaptation Issue (blocker labels: blocker:依赖链断裂(qtwebengine)
+ blocker:平台API缺失(qtbase PrintSupport)).

Upstream hard-depends on QtWebEngine:
- top CMakeLists: `find_package(Qt6 ... REQUIRED COMPONENTS ... PrintSupport
  WebEngineQuick)`,
- main.cpp: unconditional `QtWebEngineQuick::initialize()`,
- TextDisplay.qml: `WebEngineView` markdown preview + `printToPdf`,
- PrintingPage.qml: `QtQuick.Pdf` (`PdfMultiPageView`/`PdfDocument`),
- src/CMakeLists: links `Qt::WebChannel`, `Qt::PrintSupport`, `Qt6::WebEngineQuick`.

No qtwebengine recipe exists on ohpcd and porting it is out of scope, so this
port introduces the upstream option `KLEVER_WITH_WEBENGINE` (default OFF):

| Piece | ON (upstream) | OFF (this port) |
| --- | --- | --- |
| Preview | TextDisplay.qml (WebEngineView + WebChannel) | TextDisplayNative.qml (pure QML rich-text TextArea) |
| Print page | PrintingPage.qml (QtQuick.Pdf viewer) | dropped from the QML module |
| PDF printing | WebEngineView::printToPdf + PrintingUtility (QPrinter) | dropped (printingHelper.cpp out of SOURCES) |
| Print dialog | "Print to PDF" entry | entry hidden at runtime (`printingAvailable`), "Print html" export kept (feeds from `renderedHtml`) |
| find_package/link | PrintSupport + WebEngineQuick + WebChannel | none of them |

The HTML export path stays functional on OFF: EditorView falls back to
`display.renderedHtml` (the parser HTML rendered by the native preview)
instead of `display.view.runJavaScript(...)`.

Known degradations of the OFF path (documented; covered by the user-accepted final decision of 2026-09-21):
- preview CSS theming (StyleHandler CSS) is ignored by the Qt rich-text engine,
- copy-to-clipboard links inside the preview (`copy:` scheme) are unavailable,
- PDF export/printing is unavailable.

qtbase/6.11.1 does NOT ship PrintSupport (verified in the ohpcd package: no
`libQt6PrintSupport.so`, no `Qt6PrintSupport` cmake dir) — so even the ON path
would need a PrintSupport-capable qtbase; both PrintSupport and WebEngineQuick
therefore sit behind the same option.

## Dependency closure

- Qt: qtbase-sql-dbus/6.11.1 (Core/Gui/Widgets/Test/Sql/DBus), qtdeclarative/6.11.1,
  qtsvg/6.11.1. Plain qtbase/6.11.1 enters transitively via kio/6.26.0; the two
  variants coexist because every Qt lib carries a bare DT_SONAME
  (libQt6Core.so.6) resolved through LD_LIBRARY_PATH.
- KF6: kio/6.26.0 + the 6.26.0 family (karchive/kservice/kconfig/kcoreaddons/
  ki18n/kcolorscheme/kiconthemes/kcrash/kguiaddons), kirigami/6.18.0,
  kirigami-addons/1.13.0, kitemmodels/6.18.0.1, ecm/6.26.0 (tool_requires).
- kirigami-addons/1.13.0 pins the 6.18.0 family while kio/6.26.0 pins 6.26.0 →
  the root recipe declares the 6.26.0 versions with `force=True` (one version
  per package in the graph). KF6 6.x is intra-major compatible; the published
  6.18 libraries the addons' .so files link against stay resolvable on this
  device's caches (absolute NEEDED paths into ~/.conan2 / ~/.cache/conan2).
- kirigami-addons + kitemmodels are QML runtime deps klevernotes' CMake never
  declares; they are explicit conan requirements here.

## OHOS specifics carried over from the KF6 family

- `KF_IGNORE_PLATFORM_CHECK=TRUE` (OHOS not in KDE's platform list),
- `KF_SKIP_PO_PROCESSING=ON` (no msgfmt on workers),
- OHOS shared-library soname/rpath rule override (alligator 26.04.0 pattern),
- post-install ELF re-signing (llvm-objcopy --remove-section .codesign +
  binary-sign-tool) per E077 — the HMDFS W^X policy refuses to load
  post-build-written ELF files,
- link farm + absolute-NEEDED materialization for ctest/test_package (E537,
  kio test_package bridge pattern, try/except-defensive).

## Tests

- Upstream: 3 QtTest suites registered under `BUILD_TESTING`
  (src/autotests/parser/{extendedSyntax,noteLinking,emoji}Test.cpp), executed
  via `ctest` inside `build()` (conan create), offscreen env + link farm.
  Authoritative CI 2026-09-21: 3/3 ctest suites passed; QTest function-level
  totals: extendedSyntax 23/0, noteLinking 13/0, emoji 23/0 passed/failed —
  59/59 functions (evidence: device tmp/oh-device-porting-v2/
  klevernotes-1.3.1-qtest-counts.log; CI log klevernotes-1.3.1-ci16.log).
- New OHOS-specific: test_package/test_ohos_gate.py — pure-python ELF64
  DT_NEEDED parser asserting the WebEngine/Pdf/WebChannel/PrintSupport
  pipeline is ABSENT from the packaged binary and the QML + KIO closure is
  PRESENT (validates the partial-adaptation contract on the artifact itself),
  plus an offscreen launch smoke of the packaged app (timeout exit 124 ==
  engine loaded Main.qml).

## Other OHOS degradations discovered during porting (beyond WebEngine)

- qqc2-desktop-style (org.kde.desktop QQC2 style) is not published to ohpcd →
  new option `KLEVER_QQC2_DESKTOP_STYLE` (default ON = upstream behavior);
  the OHOS recipe sets it OFF and main.cpp then selects the built-in Basic
  style. (The published qtdeclarative also ships a trimmed QQuickStyle —
  no `availableStyles()` — hence the compile-time option instead of a
  runtime probe.)
- The published kiconthemes package ships no QML module (org.kde.iconthemes)
  → the import is isolated in the new KIconDialog.qml wrapper and
  ItemPropertiesDialog degrades to a plain icon-name text field (runtime
  detection; the wrapper is never statically referenced so a missing module
  cannot fail the UI load).
- Widgets include path: upstream reached <QApplication>/<QTextEdit>
  transitively via Qt6::PrintSupport; with PrintSupport gated off the OFF
  path links Qt::Widgets explicitly (patch 0002).

## Porting log (condensed)

16 CI rounds: r1 R38 commands.json; r2 new-file patch needed `--- /dev/null`;
r3 QtWidgets transitive include; r4 QIcon include; r5 link-farm level for
ctest; r6/7 test_package conan API + QQC2 style; r8/9 device-load transients
(fork EAGAIN, OpenMP probe fail under a concurrent 33-core job); r10-15
org.kde.iconthemes degradation (import isolation + runtime lookup). r16 PASS.
