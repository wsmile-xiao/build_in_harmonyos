# 适配笔记 — highway 1.3.0 (Google SIMD 向量化运算库)

## 2026-07-24 适配

### 库信息
- **软件**: highway (Google)
- **版本**: 1.3.0
- **构建系统**: CMake
- **许可证**: BSD-3-Clause
- **上游**: https://github.com/google/highway
- **功能**: 跨平台 SIMD 指令封装，aarch64 下自动选用 NEON 路径

### 依赖
- **运行时**: 零依赖

### 本地验证记录
| 检查项 | 结果 |
|--------|------|
| conan export | ✅ 成功 |
| SHA256 | ✅ e8d69690 |
| test_package | ✅ LoadU/Add/StoreU 向量运算覆盖 |
