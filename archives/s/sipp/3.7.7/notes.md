# SIPp 3.7.7 OpenHarmony PC adaptation notes

## Summary

SIPp is a traffic generator and test tool for the SIP protocol. The recipe builds the upstream CMake project and disables optional SSL, PCAP, SCTP, and GSL support to keep the base package self-contained for cross-build CI.

## Build and test

- Build system: CMake
- Upstream source: `https://github.com/SIPp/sipp/releases/download/v3.7.7/sipp-3.7.7.tar.gz`
- SHA256: `e55b15f567760e9febeef366a1ab51a5239d197a132ce931b78c826d22d31e69`
- Disabled options: SSL, PCAP, SCTP, GSL, static linking, ASAN
- Conan smoke test: runs `sipp -v` from the packaged binary.

## OpenHarmony notes

The core SIPp executable builds without extra third-party libraries when optional protocol extensions are disabled. This avoids depending on system OpenSSL, libpcap, lksctp-tools, or GSL in the base adaptation.
