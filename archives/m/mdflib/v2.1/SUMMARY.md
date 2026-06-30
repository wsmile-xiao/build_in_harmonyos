# mdflib v2.1 — 编译总结

## 基本信息

| 项目 | 内容 |
|------|------|
| 软件 | mdflib (ASAM MDF 测量数据格式读写库) |
| 版本 | v2.1.0 |
| 状态 | **published** |
| 平台 | OpenHarmony (OHOS) aarch64 |
| 构建系统 | CMake (C++17) |
| 编译器 | Clang 15.0.4 |
| 编译日期 | 2026-06-23 |

## 编译产物

| 产物 | 文件 | 大小 |
|------|------|------|
| 静态库 | lib/libmdf.a | 4.8 MB |
| 动态库 | lib/libmdflibrary.so | 1.7 MB |
| 头文件 | include/mdf/ (25), include/mdflibrary/ (17) | 42 files |
| CMake 配置 | lib/cmake/mdflib/ | 4 files |
| 预编译包 | packaging/mdflib-v2.1-ohos-aarch64.tar.gz | 6925 KB |
| 调试符号包 | packaging/mdflib-v2.1-ohos-aarch64-debug.tar.gz | 620 KB |

## 依赖

| 依赖 | 版本 |
|------|------|
| zlib | 1.3.1 |
| expat | 2.7.1 |

## 补丁

| 补丁文件 | 说明 |
|----------|------|
| 0001-mdflib-src-platform.cpp.patch | strerror_r POSIX 兼容修复 (+3/-5, 1 file) |

## 质量门禁

| 门禁 | 结果 |
|------|------|
| G1: 源码完整性 | ✅ PASS |
| G2: 补丁有效性 | ✅ PASS (⚠️ 1 advisory) |
| G3: 产物完整性 | ✅ PASS |
| G4: manifest 规范 | ✅ PASS |

## 测试

独立功能测试程序 8 项全部通过：
- MDF3/MDF4 文件对象创建
- MDF3/MDF4 文件写入（含采样数据）
- MDF3/MDF4 文件读取验证（MdfReader）
- BusLogger 写入器创建
- FinalizeMeasurement 空测量

详见 `reports/test-report.md`。

## 知识沉淀

- E081: strerror_r 在 musl libc 中返回 int (POSIX) 而非 char* (GNU)
- CMake FindEXPAT 需手动指定 -DEXPAT_LIBRARY（仅有 .so 无 .a）
- mdflib 自带 GTest 套件依赖 Boost 编译库，当前环境不可用
