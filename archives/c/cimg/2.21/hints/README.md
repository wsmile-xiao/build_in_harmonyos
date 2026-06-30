# CImg Header-only Library Installation Guide

## Special Handling Required

CImg is a **header-only library** (CImg.h only). Traditional configure/make/install 
process does NOT apply.

### Installation Steps

1. **Extract tarball**: `tar -xzf cimg-2.21.tar.gz`
2. **Locate CImg.h**: In the top-level directory
3. **Install header**:
   ```bash
   mkdir -p $PREFIX/include
   cp CImg.h $PREFIX/include/
   ```
4. **Install documentation** (optional):
   ```bash
   mkdir -p $PREFIX/share/doc/cimg
   cp README.md README.txt $PREFIX/share/doc/cimg/
   mkdir -p $PREFIX/share/licenses/cimg
   cp Licence_CeCILL-*.txt $PREFIX/share/licenses/cimg/
   ```

### Why No Traditional Build?

- CImg.h is a self-contained header file (2.7MB)
- No compilation needed, just copy to include directory
- Optional dependencies (X11, libjpeg, etc.) for advanced features
- CMakeLists.txt/Makefile only for compiling demo programs

### init-build Nested Detection Issue

The init-build script detects `examples/` as source directory and elevates it,
but **misses top-level files** (CImg.h, README.md, Licence files).

**Workaround**: Manually extract missing files from tarball:
```bash
tar -xzf cimg-2.21.tar.gz GreycLab-CImg-*/CImg.h
tar -xzf cimg-2.21.tar.gz GreycLab-CImg-*/README.md
tar -xzf cimg-2.21.tar.gz GreycLab-CImg-*/Licence_*.txt
```

### Verification

After installation:
```bash
ls -lh $PREFIX/include/CImg.h
# Should show ~2.7MB header file
```

### Usage in C++ Code

```cpp
#include "CImg.h"
using namespace cimg_library;

// Your image processing code...
```

Compile with: `clang++ -I$PREFIX/include your_code.cpp`
