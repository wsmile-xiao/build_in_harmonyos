# xq — Command-line XML and HTML beautifier and content extractor

## Overview
xq is a command-line XML and HTML beautifier and content extractor written in Go.
It allows you to format, query, and extract data from XML and HTML documents using XPath expressions.

## Key Features
- XML/HTML beautification and formatting
- XPath query support for content extraction
- JSON output mode (-j flag)
- Syntax highlighting with terminal colors
- Charset encoding handling (UTF-8 enforcement)
- Static binary (CGO_ENABLED=0) for easy deployment

## Source
- GitHub: https://github.com/sibprogrammer/xq
- License: MIT

## OpenHarmony Build Notes
- Build system: custom (Go build)
- Toolchain: Go 1.25.4 (from goenv)
- CGO_ENABLED=0 for static compilation
- ELF signature required for HarmonyOS execution
- GOPROXY=https://goproxy.cn,direct for dependency download