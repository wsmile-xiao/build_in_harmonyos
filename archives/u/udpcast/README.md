# UDPcast

UDPcast transfers files over a LAN with UDP multicast or point-to-point UDP.
The package provides separate sender and receiver command-line programs.

## Features

- Send one input stream to one or more receivers.
- Use multicast, broadcast, or point-to-point discovery and transfer modes.
- Add forward error correction to tolerate packet loss.
- Apply configurable bandwidth and transfer timing controls.

## OpenHarmony adaptation

- `config.guess` and `config.sub` are patched to recognize HarmonyOS and the
  `aarch64-unknown-linux-ohos` tuple.
- The recipe explicitly preserves `BB_FEATURE_UDPCAST_FEC`; upstream normally
  adds this through its default `CFLAGS`, but Conan supplies `CFLAGS` itself.
- A focused `configure` patch keeps temporary directories writable on HMDFS.
- The return-channel thread uses cooperative C11 atomic shutdown without an
  OpenHarmony-specific preprocessor branch because OpenHarmony does not provide
  `pthread_cancel`.
- `udp-sender` and `udp-receiver` are installed in `bin/`; their man pages and
  the public rate governor header are retained.

## Dependencies

UDPcast has no third-party Conan dependencies. It uses libc, pthread, and libdl
from the target platform. Perl and m4 are build tools used for man-page
generation.

## References

- Homepage: https://udpcast.linux.lu/
- Source mirror: https://deb.debian.org/debian/pool/main/u/udpcast/
