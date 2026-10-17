# plotutils

GNU plotutils — 2-D vector graphics library and command-line plotting utilities.

- **libplot**: C function library for device-independent 2-D vector graphics (PNG, SVG, PS, PCL, HP-GL, Fig, CGM, PNM, Tektronix, GNU Metafile)
- **libplotter**: Optional C++ wrapper class library (disabled by default)
- **CLI tools**: graph, plot, spline, ode, tek2plot, plotfont, pic2plot

## Adaptation Status

| Version | Status | Notes |
|---------|--------|-------|
| 2.6 | adapting | `--without-x` mode; PNG/PS/SVG/PNM/CGM output verified |

## Dependencies

- libpng (PNG output support)
- zlib (indirect, via libpng)
- X11 libs (optional, disabled in `--without-x` mode)
