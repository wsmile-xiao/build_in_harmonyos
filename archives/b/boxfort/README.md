# boxfort

boxfort 0.1.2 is packaged for OpenHarmony as a C99 static library.

- Library: `include/boxfort.h`, `lib/libboxfort.a`
- Conan reference: `boxfort/0.1.2`
- Consumers must build with `BXF_STATIC_LIB=1` (mirrors upstream pkg-config `extra_cflags`); the recipe exports it via `cpp_info.defines`.

The recipe uses the upstream Meson build (`default_library=static`) and has no Conan dependencies. Two platform policies required adaptation, both handled by **runtime capability probing** (pure POSIX, no platform macros — systems where the probes succeed keep the exact upstream behavior; see `0.1.2/notes.md`): code-page integrity (XPM) forbids the upstream self-exec + main-text-patchup sandbox handshake, so the sandbox falls back to running its function directly in the forked child; and a user-VA cap near 512 GiB moves the arena placement window to a low fallback range. The upstream cram functional test is not registered because the `cram` program is unavailable; its three command groups were executed manually with matching output.
