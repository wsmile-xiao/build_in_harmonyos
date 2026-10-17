# stm32flash 0.7

Conan package for the official SourceForge stm32flash 0.7 release.

## Build

```bash
conan create . -pr ohos-aarch64
```

The original Makefile is used directly with the compiler and archiver supplied
by the OHOS Conan profile. No generated configure or Makefile patch is needed.

## Validation

`test_package` executes the installed binary, validates its help output, and
exercises the real serial-port open failure path with a nonexistent device.
