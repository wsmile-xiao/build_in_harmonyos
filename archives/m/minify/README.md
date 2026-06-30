# Minify

Go-based minifier for web files (HTML, CSS, JS, JSON, SVG, XML).

## Description

Minify is a fast minifier written in Go that can compress HTML, CSS, JavaScript, JSON, SVG, and XML files. It provides both a command-line tool and a library API.

Key features:
- High-performance minification algorithms
- Supports multiple file formats
- Stream-based processing for large files
- Configurable minification options

## Homepage

https://github.com/tdewolff/minify

## License

MIT

## Usage

```bash
minify --version
minify input.html -o output.html
minify --type css input.css -o output.css
```

## Available Versions

- **2.24.13** (built, 2026-05-22)

## Notes

- Precompiled binary (Go linker issues on HMDFS file system)
- Debug symbols package contains placeholder (binary was stripped before packaging)
- Full functionality available

## Installation

Download the precompiled package `minify-2.24.13-ohos-aarch64.tar.gz` and extract it.

```bash
tar -xzf minify-2.24.13-ohos-aarch64.tar.gz -C ~/usr/local/
```