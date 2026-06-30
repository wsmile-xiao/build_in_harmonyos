# OpenColorIO

OpenColorIO (OCIO) is a complete color management solution geared towards motion picture production with an emphasis on visual effects and computer animation.

## Features

- Complete color management pipeline
- Color space transformations
- Look development and management
- Integration with major VFX and animation tools
- Industry-standard color configurations

## Dependencies

- pystring >= 1.1.5
- yaml-cpp >= 0.7.0

## Build

```bash
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DOCIO_BUILD_TESTS=OFF \
  -DOCIO_BUILD_APPS=OFF \
  -DOCIO_BUILD_PYTHON=OFF
make -j2
make install
```

## Version History

- 2.2.1: Latest stable release