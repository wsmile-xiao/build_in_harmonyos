# Project IceStorm 1.1

- Builds `icepack`, `iceunpack`, `icemulti`, `icepll`, `icebram`, and
  `icetime` with the OHOS Clang toolchain.
- The optional `iceprog` hardware programmer is disabled because it requires
  direct USB device access and libusb.
- The upstream timing tests require Yosys and the hardware-oriented icebram
  demo uses generated files, so neither is silently counted as executed.
- The consumer test validates five installed command-line entry points and a
  real PLL calculation.
- Official OHOS test and CI results remain pending.
