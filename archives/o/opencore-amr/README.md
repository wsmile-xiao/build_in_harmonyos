# opencore-amr — Adaptive Multi-Rate (AMR) speech codec library

opencore-amr provides implementations of the AMR-NB (Adaptive Multi-Rate Narrowband)
and AMR-WB (Adaptive Multi-Rate Wideband) speech codecs, derived from the OpenCore
codec implementation.

## Features

- AMR-NB encoder and decoder (GSM 06.90 / 3GPP TS 26.071)
- AMR-WB encoder and decoder (3GPP TS 26.190 / 26.204)
- Lightweight library with no external dependencies
- Used by multimedia frameworks for AMR audio encoding/decoding

## Current Build Configuration

The current build (0.1.6) uses autotools with minimal configuration:
- Only `--prefix` specified (no additional configure options)
- Requires config.guess/config.sub patches for HarmonyOS platform detection
- No external dependencies required
- Both static and shared libraries built successfully

## Homepage

https://sourceforge.net/projects/opencore-amr/