# libnexstar

libnexstar is a C library for controlling Celestron NexStar and SkyWatcher/Orion SynScan telescope mounts over serial or TCP connections.

## Features

- Telescope alignment, coordinate, tracking, slew, time, location, and model commands
- Celestron NexStar and SkyWatcher/Orion protocol variants
- Periodic error correction (PEC) operations
- Decimal-degree and telescope-protocol coordinate conversions
- RS-232 and TCP transports

## HarmonyOS adaptation

The 0.15 release is built for HarmonyOS PC AArch64 with its Autotools build. The bundled GNU configuration scripts are extended to recognize the `aarch64-linux-ohos` triplet, and source-local headers are made compatible with clean VPATH builds. Both shared and static Conan package variants are supported; the shared variant is the default because HarmonyOS does not provide a system `libnexstar` with the same name.

## Dependencies

libnexstar has no third-party dependencies. It uses the C library, POSIX serial/socket APIs, and the system math library.

## References

- Homepage and releases: https://sourceforge.net/projects/libnexstar/
- Source archive: https://downloads.sourceforge.net/project/libnexstar/libnexstar-0.15.tar.gz
