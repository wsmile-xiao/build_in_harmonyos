# mbpoll

mbpoll is a command line utility to communicate with ModBus slave devices over
serial (RTU) or TCP. It can read discrete inputs, read/write coils, read input
registers and read/write holding registers, with decimal/hexadecimal/float
display.

- Upstream: https://github.com/epsilonrt/mbpoll
- License: GPL-3.0-only
- Build system: CMake

## OHOS adaptation notes

- **libmodbus dependency is vendored.** mbpoll requires libmodbus (>= 3.1.7),
  which is not published as a Conan package in the OHOS artifact registry. The
  recipe therefore downloads the official libmodbus 3.1.7 release tarball, builds
  it as a static library, and links mbpoll against it via pkg-config. The shipped
  package contains only the `mbpoll` executable.
- **`linux/serial.h` shim.** The musl-based OHOS toolchain lacks the
  `linux/serial.h` kernel header that libmodbus' `modbus-rtu.c` includes for the
  RS485 ioctl. A minimal, standard definition is provided on the include path.
- **Version hardcoding.** Upstream derives the version from git tags via
  `cmake/GitVersion.cmake`, which hard-aborts the configure step when the source
  tree is not a git repo carrying a matching tag. A patch hardcodes the version
  (1.5.4) instead.
- **piduino disabled.** GPIO-based RS-485 RTS control (piduino) is unavailable on
  OHOS and is turned off.
