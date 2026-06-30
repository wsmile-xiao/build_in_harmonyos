# manticore

## What is it?

Manticore Search is a fast, open-source full-text search engine that evolved from Sphinx Search. It supports multi-core parallelism, real-time indexing, and various query types.

## Key Features

- Full-text search with advanced query syntax
- Real-time and batch indexing modes
- Multi-core parallel query processing
- SQL, HTTP, and JSON API support

## OHOS/HarmonyOS Adaptation

- **Build type**: cmake
- **2 patches required**:
  - src/CMakeLists.txt — platform adaptation
  - src/gtests/CMakeLists.txt — test adaptation
- **Large build**: 412MB release package, 80MB debug package

## Version 6.7.0

- Status: published
- Build date: 2026-06-09
- 2 patches applied for platform compatibility