# ffuf - Fuzz Faster U Fool

A fast web fuzzer written in Go.

## Description

ffuf is a fast web fuzzer that allows for flexible and efficient fuzzing of web applications. It supports various fuzzing modes including URL path, query parameters, headers, POST data, and more.

## Features

- Multiple fuzzing modes (URL, headers, POST data, etc.)
- Recursive fuzzing support
- Automatic calibration
- Multiple output formats (JSON, CSV, HTML, Markdown)
- Interactive mode
- Proxy support
- Rate limiting

## Compiled Version

- Version: 2.1.0-r21
- Build System: Go (custom)
- Platform: OpenHarmony linux/arm64

## Installation

Use the cmd-pkgs public install script:

```bash
curl install.sh | sh -s -- ffuf 2.1.0-r21
```

## Usage

```bash
ffuf -u https://example.com/FUZZ -w wordlist.txt
ffuf -V  # Show version
```
