# libepoxy

libepoxy is a library for handling OpenGL function pointer management.

## Version
- 1.5.10 (stable)

## Description
Epoxy is a library for handling OpenGL function pointer management for you.
It hides the complexity of `dlopen()`, `dlsym()`, `glXGetProcAddress()`,
`eglGetProcAddress()`, etc. from you.

## OpenHarmony Build Notes
- Built with minimal configuration (no GLX/EGL/X11 support)
- Requires OpenGL headers only (no runtime OpenGL library dependency)
- Built as shared library with ELF signature

## Dependencies
- libdl (system provided)

## Installation
```bash
curl -fsSL <url>/libepoxy-1.5.10-ohos-aarch64.tar.gz | tar xz
cd libepoxy-1.5.10-ohos-aarch64
./install.sh ~/usr/local
```

## Verification
```bash
pkg-config --modversion epoxy
# Output: 1.5.10
```

## License
MIT License

## Source
https://github.com/anholt/libepoxy
