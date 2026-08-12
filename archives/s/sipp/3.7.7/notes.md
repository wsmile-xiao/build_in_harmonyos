# SIPp 3.7.7 OpenHarmony PC adaptation notes

## Summary

SIPp is a traffic generator and test tool for the SIP protocol. The recipe builds the upstream CMake project and disables optional SSL, PCAP, SCTP, and GSL support to keep the base package self-contained for cross-build CI.

## Build and test

- Build system: CMake
- Upstream source: `https://github.com/SIPp/sipp/releases/download/v3.7.7/sipp-3.7.7.tar.gz`
- SHA256: `e55b15f567760e9febeef366a1ab51a5239d197a132ce931b78c826d22d31e69`
- Disabled options: SSL, PCAP, SCTP, GSL, static linking, ASAN
- Private build dependency: ncurses 6.5 is downloaded and built inside the SIPp build folder to satisfy SIPp's required curses UI linkage without submitting a second Conan recipe in this PR.
- Conan smoke test: runs `sipp -v` from the packaged binary, accepts SIPp's documented informational exit code `99` (`EXIT_OTHER`), and verifies that the emitted banner still contains SIPp help/version text rather than assuming a single exact output line.
- Upstream unit tests: the recipe depends on `gtest/1.17.0`, builds the upstream `sipp_unittest` target, registers it as a CTest case, and runs `ctest --output-on-failure` so the 50 upstream TEST cases compiled under this configuration are verified in the OHOS build (source has 53; 1 SHA-256 and 2 PCAPPLAY cases are behind optional features disabled in path A).

## OpenHarmony notes

The core SIPp executable builds with optional protocol extensions disabled, avoiding system OpenSSL, libpcap, lksctp-tools, or GSL in the base adaptation. SIPp still requires curses for its UI code path, so the recipe builds ncurses 6.5 privately inside the SIPp build tree and links that static library directly. The ncurses files are not submitted as a separate archive recipe in this PR.
