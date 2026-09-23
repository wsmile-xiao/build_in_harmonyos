# libcsptr

[libcsptr](https://github.com/Snaipe/libcsptr) — C smart pointer library (MIT).

Provides `smalloc`/`sfree` based smart pointers: unique/shared/array pointer
macros with optional destructors and metadata, implemented in pure C99.

- 版本: 2.0.4
- 构建系统: CMake (static library `libcsptr.a`)
- 平台: HarmonyOS PC (arm64 / aarch64-linux-ohos)
- 适配状态: built

## 归档

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.4 | built | conan-verify G0-G4 PASS; W3 本地 CI 全过; 上游测试依赖可选 Check 框架(未装时 ctest 0/0) |
