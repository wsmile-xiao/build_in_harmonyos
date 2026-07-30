# libldac aosp-20250110

Conan package for the AOSP LDAC encoder and adaptive bitrate controller at the
official 2025-01-10 source revision.

## Build

```bash
conan create . -pr ohos-aarch64
```

The upstream project uses Android.bp only. The included patch adds a portable
CMake build for the same `libldacBT_enc` and `libldacBT_abr` source sets.

## Validation

`test_package` links both installed libraries, allocates encoder and ABR
handles, initializes 48 kHz stereo encoding, and validates their public state.
