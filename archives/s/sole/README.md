# sole

Sole 是一个轻量级 C++11 头文件库，用于生成通用唯一标识符（UUID），提供 v0/v1/v4 三个版本。

## 功能概述
- `sole::uuid` 128 位 UUID 基础类型：比较、排序、`std::ostream <<` 输出
- `.str()` 十六进制字符串、`.base62()`、`.pretty()` 分解报告
- `sole::uuid0()`（PID+MAC+时钟）、`sole::uuid1()`（MAC+时钟）、`sole::uuid4()`（纯随机）
- `sole::rebuild()` 从字符串/64 位元组重建 UUID
- Header-only、零依赖、跨平台（zlib/libpng 许可）

## OHOS 适配
- Header-only 库，无编译阶段，配方采用 headeronly 变体（v12.21 模板）
- 补丁 0001：uuid4() 的 thread-local `std::random_device`/`std::uniform_int_distribution`
  由 `__thread` 改为标准 C++11 `thread_local`（clang 15 对非平凡析构类型拒绝 `__thread`）
- 上游内建测试（SOLE_BUILD_TESTS）在 OHOS clang 15 (aarch64) 下编译、运行通过

## 依赖关系
- **编译依赖**: 无（header-only）
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/r-lyeh/sole
- 文档: https://github.com/r-lyeh/sole (README.md)