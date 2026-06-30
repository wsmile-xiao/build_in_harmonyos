# CImg - C++ Template Image Processing Library

## Description

CImg is a small, open-source, and **header-only** C++ library for image processing.
It is designed to be **useful, generic, portable, simple, and extensible**.

## Key Features

- **Header-only**: Single CImg.h file (~2.7MB), no compilation required
- **4D images**: Supports 1D-4D datasets (scalar signals to volumetric hyperspectral images)
- **Template pixel types**: bool, char, int, float, etc.
- **Portable**: Works on Unix, Windows, MacOS X, BSD, etc.
- **Thread-safe**: Self-contained, minimal dependencies

## Optional Dependencies

- **X11**: Graphics display (optional)
- **libjpeg/libpng/libtiff**: Image format support (optional)
- **FFTW3**: Fast Fourier Transform (optional)
- **OpenCV**: Computer vision (optional)
- **ImageMagick/Magick++**: Advanced image formats (optional)
- **FFMPEG**: Video support (optional)

## Installation

Just copy CImg.h to your include directory:
```bash
cp CImg.h /usr/local/include/
```

Or install from precompiled package:
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cimg 2.21
```

## Usage

```cpp
#include "CImg.h"
using namespace cimg_library;

CImg<float> image("input.jpg");  // Load image
image.blur(2.0);                 // Apply Gaussian blur
image.save("output.jpg");        // Save result
```

## License

Dual-licensed:
- **CeCILL-C** (LGPL-like): Allows commercial use
- **CeCILL** (GPL-compatible): Requires open source

## Versions

- **2.21** (latest): Current stable version

## Links

- Website: http://cimg.eu
- GitHub: https://github.com/GreycLab/CImg
- Documentation: http://cimg.eu/reference/
