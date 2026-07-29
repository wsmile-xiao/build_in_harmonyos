# imgui

Dear ImGui is a bloat-free immediate-mode graphical user interface library
for C++. This archive entry provides a Conan package for the upstream
`v1.92.2b` release and supports Linux and OpenHarmony consumers.

The release archive does not contain a formal upstream test suite. The Conan
consumer test validates the public version/layout check, context and IO/style
lifecycle, and rejection of an intentionally mismatched version. On OHOS, the
package also provides a Native XComponent platform backend for surface,
touch/mouse, and keyboard events, plus the upstream OpenGL3 renderer compiled
for GLES3. The OHOS consumer test creates an EGL pbuffer and renders real Dear
ImGui draw data.
