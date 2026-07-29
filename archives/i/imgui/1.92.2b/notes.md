# imgui 1.92.2b adaptation notes

- Source: official GitHub `v1.92.2b` release archive.
- Source SHA-256: `da3d453cce74e0fb3d67f8d798a2a8d04fcaf0b33ce0e0131d0695dfc4f64191`.
- Upstream has no root build definition and no formal test runner in this
  release archive. The recipe generates a minimal CMake build for the five
  official core translation units.
- On OHOS, the recipe additionally builds a real Native XComponent platform
  backend. It registers surface, touch, mouse, and keyboard callbacks and maps
  those events to the modern Dear ImGui input queue.
- On OHOS, the upstream OpenGL3 renderer backend is compiled in GLES3 mode and
  the package declares `ace_ndk.z`, `EGL`, and `GLESv3` system dependencies.
- The OHOS backend sources are maintained as recipe-owned sources under
  `sources/` and copied into the exact upstream source tree by the recipe.
- The public headers and the MIT license are packaged.
- The consumer test exercises real Dear ImGui context, IO, and style APIs.
  On OHOS it also validates touch/key/unicode mapping, creates a real EGL
  pbuffer and GLES3 context, and renders non-empty Dear ImGui draw data.
- The explicit `--ohos-headless` mode is for direct `hdc shell` validation,
  where no application EGL display is available. It still verifies the OHOS
  input queue, font atlas, and non-empty draw data on the PC emulator.
- The fault mode deliberately supplies an invalid version to the public layout
  compatibility check and requires rejection.
