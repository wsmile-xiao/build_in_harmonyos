# arduino-mighty-1284p

Arduino ATmega1284P platform package by maniacbug.

## Contents

- **cores/standard/** — Arduino core library (C/C++ source and headers)
- **bootloaders/optiboot/** — Optiboot bootloader for ATmega1284P
- **bootloaders/standard/** — ATmegaBOOT bootloader
- **variants/** — Pin configuration headers for different board variants
- **boards.txt** — Arduino IDE board definitions

## Adaptation Notes

This is a header/source-only package. The source files are designed for AVR
microcontrollers (ATmega1284P) and use AVR-specific headers (`<avr/io.h>`,
`<avr/interrupt.h>`, `<avr/pgmspace.h>`). They cannot be compiled on OHOS aarch64.

The Conan package provides the source files as-is for consumers that have
an AVR cross-compilation toolchain.
