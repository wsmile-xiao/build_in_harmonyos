# libdebugutils

`libdebugutils` packages the DebugUtils drawing helpers from Recast Navigation, used to render navigation meshes, geometry, and debug overlays.

## Features

- Debug drawing primitives and color helpers through `DebugDraw.h`.
- Recast heightfield, contour, polygon mesh, and Detour navigation mesh drawing APIs.
- `duDisplayList` for recording and replaying debug draw calls.

## HarmonyOS adaptation

- Builds from the upstream Recast Navigation `v1.6.0` source with its demo and examples disabled.
- Keeps upstream Catch2 tests enabled and runs the consumer tests against the HarmonyOS target.
- Set `OHOS_SDK_NATIVE` to the installed SDK native directory; set `OHC_HDC_TARGET` to run cross-built tests on an attached HarmonyOS PC VM through hdc.
- No HarmonyOS source patch is needed. The package is static by default and contains the static link closure (`DebugUtils`, `DetourTileCache`, `Detour`, and `Recast`) so consumers do not need unpublished Conan dependencies.

## Dependencies

- Conan build dependencies: none.
- Runtime dependencies: HarmonyOS system C/C++ runtime and math library.

## References

- [Recast Navigation source repository](https://github.com/recastnavigation/recastnavigation)
- [Recast Navigation v1.6.0 release](https://github.com/recastnavigation/recastnavigation/releases/tag/v1.6.0)
- [Recast Navigation DebugDraw API](https://recastnav.com/DebugDraw_8h.html)
