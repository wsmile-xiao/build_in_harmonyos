# libzippp

## 简介
libzippp 是 libzip 的 C++ 封装库，提供面向对象的 ZIP 归档操作接口（ZipArchive/ZipEntry），
支持建包、读包、条目增删、内存缓冲区归档等操作。

## OHOS 适配
- **构建系统**: CMake（单源文件 src/libzippp.cpp，C++11）
- **依赖链**: libzip（→ zlib）
- **上游仓库**: https://github.com/ctabin/libzippp（已从 ctasada/libzippp 迁移）
- **版本索引**:
  - 7.1-1.10.1 — 2026-09-20 适配（tag libzippp-v7.1-1.10.1，对应 libzip 1.10.x，兼容制品仓 libzip/1.11.4）
