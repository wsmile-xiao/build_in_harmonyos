# SVGO

Node.js tool for optimizing SVG files.

## Description

SVGO (SVG Optimizer) is a Node.js-based tool for optimizing SVG vector graphics files. It removes unnecessary metadata, simplifies paths, and applies various optimizations to reduce file size while maintaining visual quality.

Key features:
- Plugin-based optimization architecture
- Extensive list of built-in optimization plugins
- Presets for common optimization scenarios
- CLI and programmatic API

## Homepage

https://github.com/svg/svgo

## License

MIT

## Usage

```bash
svgo --version
svgo input.svg -o output.svg
svgo *.svg -o ./optimized/
```

## Available Versions

- **4.0.1** (built, 2026-05-22)

## Notes

- Includes rollup native module for OpenHarmony ARM64
- All core functionality works on HarmonyOS
- Native module may have limited runtime support but build functionality is available

## Installation

Download the precompiled package `svgo-4.0.1-ohos-aarch64.tar.gz` and extract it.

```bash
tar -xzf svgo-4.0.1-ohos-aarch64.tar.gz -C ~/usr/local/
```