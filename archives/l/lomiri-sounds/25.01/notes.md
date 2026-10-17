# lomiri-sounds 25.01 adaptation notes

- The upstream project is a CMake data package. It installs the complete
  `share/sounds` tree and `data/lomiri-sounds.pc`; no compiled dependency is
  declared by Debian's package metadata.
- The Conan recipe keeps the upstream relative paths and sets
  `CMAKE_INSTALL_DATADIR=share` so the package root contains
  `share/sounds/lomiri`.
- There is no upstream test suite. The independent consumer checks the
  installed resource count, four representative files, and non-empty bytes.
- Source archive: 18,823,555 bytes, SHA-256
  `00aeb6c36ef311145a270deffc02728067ef3bd18c00d3a90353712eadf2cc8c`.
