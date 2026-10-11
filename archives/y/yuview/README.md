# yuview

YUView is a Qt based, cross-platform YUV player with an advanced analytic
toolset. This archive contains its HarmonyOS PC adaptation.

| Version | Status | Notes |
|---|---|---|
| 2.14 | Built and locally verified | qmake build of YUViewLib plus YUView; 11/11 upstream unit tests pass; GUI requires a QPA platform plugin, so validation uses the CLI, the library API and the upstream tests |

## What is packaged

| Path | Content |
|---|---|
| `bin/YUView` | The application executable |
| `sdk/YUViewLib/libYUViewLib.a` | The upstream analytics/pixel-format static library as built (upstream itself does not install it) |
| `sdk/YUViewLib/src/**/*.h` | Headers for that library |

## Build system

qmake (top level `YUView.pro` subdirs project). `qtbase/6.11.1.3` supplies the
`qmake6` used for the build and the `harmonyos-clang` mkspec.

## Configuration used

```
qmake6 -spec harmonyos-clang CONFIG+=UNITTESTS CONFIG+=release CONFIG-=debug VERSION=2.14 YUView.pro
make -j<n>
```

## Patches

| Patch | Purpose |
|---|---|
| `0001-YUViewApp-YUViewApp.pro.patch` | Link Qt OpenGL only when the configured Qt provides it |
| `0002-YUViewApp-src-yuviewapp.cpp.patch` | Report version/usage on the command line before constructing `QApplication` |
| `0003-YUViewLib-YUViewLib.pro.patch` | Link Qt OpenGL only when the configured Qt provides it |
| `0004-YUViewLib-src-handler-UpdateHandler.cpp.patch` | Guard Qt Network SSL APIs with `QT_CONFIG(ssl)` |
| `0005-YUViewLib-src-handler-UpdateHandler.h.patch` | Forward declare `QSslError` only when SSL is available |
| `0006-YUViewLib-src-video-VideoCache.cpp.patch` | Include the generated moc file outside the project namespace |

## Known boundaries

- The HarmonyOS PC Qt Base build has no OpenGL module, therefore the upstream
  `QT += opengl` module dependency is made conditional rather than removed; Qt
  builds that ship OpenGL keep the original behaviour.
- The Qt Base build has no SSL support, so the optional auto-update path that
  relies on encrypted connections is compiled out through `QT_CONFIG(ssl)`.
- Displaying the GUI needs a QPA platform plugin. Only `offscreen` and
  `minimal` are available here, so a full windowed session is out of scope for
  this package; the executable is still verifiable through its CLI.
