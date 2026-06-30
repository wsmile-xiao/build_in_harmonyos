# isa-l — Intel Intelligent Storage Acceleration Library

Intel提供的高性能存储加速算法库，包含纠删码、压缩、CRC校验等功能的优化实现。

## 已编译版本

| 版本 | 状态 | 平台 | 构建系统 | 日期 |
|------|------|------|----------|------|
| 2.32.0 | built | OHOS aarch64 | autotools | 2026-06-03 |

## 适配说明

- **SVE优化已禁用**: clang 15.0.4存在`__attribute__((target("+sve")))+always_inline`兼容性问题，NEON优化完整可用
- **必须传递 `CPPFLAGS="-D__OHOS__"` 给 configure**
- **推荐静态链接**: 避免musl动态链接器路径隔离问题
- **igzip运行时需库在musl可搜索路径**

详见各版本的 `notes.md` 和 `reports/test-report.md`。