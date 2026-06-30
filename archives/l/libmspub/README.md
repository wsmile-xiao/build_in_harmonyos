# libmspub

Library for parsing Microsoft Publisher files (.pub). Part of the Document Liberation Project.

## Versions

- **0.1.2** — built 2026-06-25 (autotools, clang 15.0.4)

## Description

libmspub is a library for parsing the Microsoft Publisher file format. It provides:
- A shared library (libmspub-0.1.so) for parsing .pub files
- Command-line tools: pub2raw (raw output), pub2xhtml (XHTML output)

## Dependencies

- librevenge >= 0.0.1
- zlib
- boost (headers)
- icu-i18n

## Source

- Repository: https://github.com/LibreOffice/libmspub
- Tag: libmspub-0.1.2

## Platform Compatibility

- ✅ HarmonyOS HongMeng Kernel 1.12.0 (aarch64) — 功能测试通过
  - 命令行工具 pub2raw/pub2xhtml 正常执行
  - C++ API (MSPUBDocument::isSupported/parse) 正常工作
  - pkg-config 接口正常
  - 内存安全: 100次循环调用无崩溃
  - 详见: 0.1.2/reports/test-report.md
