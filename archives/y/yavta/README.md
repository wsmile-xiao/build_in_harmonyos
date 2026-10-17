# Yavta

Yet Another V4L2 Test Application, a command-line utility for querying and testing Video4Linux2 devices.

## OHOS adaptation

The package builds the upstream Meson project for HarmonyOS PC and includes the upstream V4L2 UAPI headers. Capture and streaming operations need an accessible `/dev/video*` device and the required permissions. `yavta --help` works without camera hardware.

## Dependencies

No runtime or Conan package dependencies.

## Verify

```sh
yavta --help
```

## Reference

- [Upstream repository](https://git.ideasonboard.org/yavta.git)
