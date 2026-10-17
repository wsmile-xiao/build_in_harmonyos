# libcamera

libcamera is a complex camera support library that provides a modern C++ API and pipeline-handler framework for camera applications.

## Functionality

- Camera manager and camera enumeration APIs
- Pixel formats, controls, requests, streams, and frame-buffer support
- Pipeline handlers and isolated IPA modules
- Meson/pkg-config metadata for downstream consumers

## OpenHarmony adaptation

The 0.7.2 Conan recipe builds shared libraries for OpenHarmony arm64 with the LLVM toolchain. The validated minimal profile enables the `uvcvideo` and `vimc` pipeline handlers and disables desktop applications, V4L2 emulation, GStreamer, udev, tracing, documentation, and other optional integrations. The package signs runnable OHOS ELF artifacts. The validation device had no camera media nodes, so physical camera discovery and hardware capture are not claimed.

The adaptation patch uses feature-detected portability paths for OHOS memfd limitations, process spawning and wait status, temporary-file locations, and nullable YAML diagnostics. Unsealed temporary-file fallback is used only where the upstream operation does not require file seals; sealed allocations are not emulated.

## Dependencies

The build uses the published `libyaml/0.2.5` and OHOS-compatible `openssl/3.5.6` Conan packages. PLY 3.11 is fetched by checksum as a host-side code-generation tool and is not installed as a runtime dependency.

## References

- Homepage: https://libcamera.org/
- Source: https://gitlab.com/libcamera/libcamera
