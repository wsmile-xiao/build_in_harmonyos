# hyperfine

A command-line benchmarking tool written in Rust.

## Description

hyperfine is a benchmarking tool that measures the execution time of commands
with statistical analysis and multiple output formats. It features:

- Statistical analysis across multiple runs
- Support for arbitrary shell commands
- Progress feedback with interim results
- Warmup runs
- Parameterized benchmarks
- Export results to CSV, JSON, Markdown, etc.

## Source

- Chimera Linux (🅲) - aarch64 musl package
- Version: 1.20.0-r0

## Build Strategy

Since rustc crashes (SIGSEGV) on the musl/HarmonyOS platform, this package
uses a precompiled binary from Alpine Linux's aarch64 musl repository.
The binary is dynamically linked against musl libc (/lib/ld-musl-aarch64.so.1).

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- hyperfine 1.20.0-r0
```

## Verification

```bash
hyperfine --version
# Output: hyperfine 1.20.0
```
