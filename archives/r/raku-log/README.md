# raku-log

A standard logging interface for applications written in the Raku programming language.

## Features

- Defines the `Log::Implementation` role for logging backends.
- Provides eight RFC5424-inspired severity levels.
- Exposes a shared `$Log::instance` for application-selected logging implementations.

## HarmonyOS adaptation

The package contains pure Raku source modules and runs with the published Rakudo MoarVM runtime for OHOS aarch64. The Rakudo package's `lib` directory must be included in `LD_LIBRARY_PATH` so `libmoar.so` can be loaded; `MVM_JIT_DISABLE=1` is set for HarmonyOS runtime execution.

## Dependencies

- Runtime: `rakudo/2025.11`, including its `nqp/2025.11` and `moarvm/2025.11` runtime closure.

## Upstream

- Repository: https://git.tyil.nl/raku/log
- License: LGPL-3.0-only
