# libg15render

libg15render is the G15Tools pixel, primitive, bitmap-font and FreeType rendering library for the 160×43 monochrome LCD found on Logitech G15-class devices. The source distribution also provides the `g15fontconvert` font conversion utility.

## Features

- Pixel, line, box, circle, progress-bar, icon, sprite and XBM rendering.
- Built-in G15 bitmap-font loading, measurement and text rendering.
- Optional TrueType rendering through FreeType, enabled in this package.
- Conversion of TrueType fonts to the native G15 bitmap-font format.

## HarmonyOS adaptation

- The 2009 Autotools input calls the removed `freetype-config` helper. The Conan recipe instead compiles the small source set directly with the profile-selected Clang and injects the published FreeType dependency.
- Portable source patches add declarations required by modern C compilers and make WBMP failure handling deterministic.
- `LIBG15RENDER_FONT_DIR` provides relocatable access to packaged default fonts; the original `/usr/share/g15tools/fonts` location remains the fallback.
- The package contains the shared or static library, public header, 40 default fonts, manual page, pkg-config metadata and `g15fontconvert`.

## Dependencies

- `freetype/2.14.3`
- System math library (`libm`)

## References

- Project: https://sourceforge.net/projects/g15tools/
- SVN r316 source: https://sourceforge.net/p/g15tools/code/316/tree/trunk/libg15render/
