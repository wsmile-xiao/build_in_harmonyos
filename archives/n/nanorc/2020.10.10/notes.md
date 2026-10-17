# nanorc build notes

## Build System
nanorc is a collection of configuration files for GNU Nano editor syntax highlighting.
No compilation is required - files are simply copied to the package directory.

## Configuration
- Uses Conan package manager
- No build steps needed
- Files are copied to share/nanorc/

## Installation
After installing the package, users should:
1. Add `include <package_path>/share/nanorc/*.nanorc` to their ~/.nanorc file
2. Or use `cat <package_path>/share/nanorc/nanorc >> ~/.nanorc`

## Platforms
- aarch64 (OHOS)
- No architecture-specific code

## Notes
- This is a pure configuration package
- No compiler or build tools required
- Test verifies that NANORC_PATH is set and files exist