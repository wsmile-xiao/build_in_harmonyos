# args

args is a single-header, header-only C++ argument parser library (Taywee/args, MIT).

## OHOS adaptation

- Builds the official v6.6.0 tarball with CMake.
- Header-only: installs `args.hxx`; consumers link the `taywee::args` INTERFACE target.
- No third-party dependencies.
- 93/93 upstream test executables compile and pass on the OHOS PC aarch64 toolchain.
- Includes a HarmonyOS-specific consumer test and a test_package consumer.

## Dependencies

- None.

## References

- Upstream: https://github.com/Taywee/args
- Recipe: `archives/a/args/6.6.0/`
