# libavc1394

Audio/Video Control library for IEEE-1394 devices.

## Description

libavc1394 is a library for controlling Audio/Video devices via the IEEE-1394 (FireWire) bus. It provides a programming interface for applications to communicate with AV/C devices like camcorders, VCRs, and other AV equipment.

The library consists of two main components:
- **libavc1394**: AVC (Audio/Video Control) command library
- **librom1394**: ROM (Configuration ROM) access library

## Dependencies

- libraw1394 >= 1.0.0

## Tools

The package includes the following command-line tools:
- `dvcont`: DV camcorder control utility
- `mkrfc2734`: Create RFC 2734 compliant unit directory

## Availability

Precompiled package available for HarmonyOS aarch64.

## Versions

- 0.5.4 (published, 2026-05-30)