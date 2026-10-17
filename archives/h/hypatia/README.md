# hypatia

**Single-file header-only C math library for 2D/3D graphics programming**

## Description

Hypatia is a pure-C, header-only math library designed for 2D/3D graphics applications such as games. Named after the Greek mathematician Hypatia (355-415 C.E.), it provides comprehensive support for:

- **Vector operations**: 2D and 3D vectors (dot product, cross product, normalization)
- **Matrix operations**: 3x3 and 4x4 matrices (transformations, projections)
- **Quaternions**: Rotation and orientation calculations
- **Single and double precision**: Compile-time choice between float and double

## Features

- **Header-only**: Just `#include <hypatia.h>` - no linking required
- **C89/C90 compliant**: Maximum portability
- **Mutable objects**: All objects (vectors, matrices, quaternions) are mutable for performance
- **Tested**: Comprehensive unit tests for all math functions
- **Verbose naming**: Clear function names like `vector3_cross_product()` instead of cryptic abbreviations

## Usage

```c
#define HYPATIA_IMPLEMENTATION
#include <hypatia.h>

int main() {
    struct vector3 a, b, result;
    
    vector3_setf3(&a, 3.0f, -3.0f, 1.0f);
    vector3_setf3(&b, 4.0f, 9.0f, 2.0f);
    vector3_cross_product(&result, &a, &b);
    
    return 0;
}
```

## Versions

- **2.0.0** (latest): Single-file header library

## Links

- **Homepage**: https://github.com/dagostinelli/hypatia
- **Documentation**: http://dagostinelli.github.io/hypatia/
- **License**: MIT
