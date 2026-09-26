# GLEW 2.3.1 OpenHarmony PC adaptation

## Source and scope

- Official release: `glew-2.3.1`
- Archive: `https://downloads.sourceforge.net/project/glew/glew/2.3.1/glew-2.3.1.tgz`
- SHA-256: `B64790F94B926ACD7E8F84C5D6000A86CB43967BD1E688B03089079799C9E889`
- Conan dependencies: none
- Package shape: static `libGLEW.a`, generated headers, license, and pkg-config metadata

The package uses upstream `SYSTEM=linux-clang-egl`, disables GLU, and builds only
`glew.lib.static`. The shared library and the `glewinfo`/`visualinfo` tools need a
platform window-system/runtime closure and are outside this dependency package.

## Adaptation

The upstream Makefile hard-codes `/tmp` for distribution staging. The patch uses
`TMPDIR` while retaining `/tmp` as the non-OHOS fallback. Because the project is a
bare Makefile build, the recipe explicitly forwards Conan's target flag, sysroot,
compiler, and archiver instead of assuming CMakeToolchain injection.

Static consumers inherit `GLEW_STATIC`, `GLEW_EGL`, `GLEW_NO_GLU`, and the OHOS
`EGL`/`GLv4` system libraries. This is required because the public header must
use the static-library API contract and references to `eglGetProcAddress` inside
the archive must be resolved when the consumer links.

## Tests

The 2.3.1 source distribution has no `test` or `check` target, so the upstream
inventory is 0/0. The Conan test package links the packaged archive through the
generated `glew::glew` target and verifies the full, major, minor, and micro
version strings through `glewGetString()`. `GLEW_VERSION_MAJOR`,
`GLEW_VERSION_MINOR`, and `GLEW_VERSION_MICRO` are API selector constants, not
numeric compile-time version macros. The OHOS/armv8 create and consumer
compile/link completed successfully before target-device execution.

Target runtime evidence is maintained outside the candidate tree under the task's
immutable W3 evidence directory.

During target preparation, HMDFS projected a requested `0750` mode for the
self-signed consumer to `0710`. Permission validation therefore binds the
security semantics actually required by execution: owner execute must be set,
group/other write must be clear, and the exact observed mode must be retained in
the receipt. A successful `chmod` alone is not sufficient evidence.
