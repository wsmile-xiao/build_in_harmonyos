# byte-lite 0.3.0 — Bootstrap 笔记（pc3-33）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/martinmoene/byte-lite （GitHub 跳转到 nonstd-lite/byte-lite 组织）
- 正式标签：`v0.3.0` → commit `dd5b3827f7cd74c1f399d1ec2c063982d3442a99`
- Release 发布时间：2020-10-17T17:51:01Z
- 许可证：Boost Software License 1.0（BSL-1.0）
- 源码 tarball：`https://github.com/martinmoene/byte-lite/archive/refs/tags/v0.3.0.tar.gz`
- SHA-256：`1a19e237b12bb098297232b0a74ec08c18ac07ac5ac6e659c1d5d8a4ed0e4813`

## 结构
- 单文件头文件库：`include/nonstd/byte.hpp`
- CMake INTERFACE library：目标 `nonstd::byte-lite`，包 `byte-lite`
- CMake 选项：`BYTE_LITE_OPT_BUILD_TESTS` / `BYTE_LITE_OPT_BUILD_EXAMPLES` / `BYTE_LITE_OPT_SELECT_STD` / `BYTE_LITE_OPT_SELECT_NONSTD`
- 上游自带 Conan 1.x 配方（`from conans import ...`）；本归档按 Conan 2.x 重写（any-lite 同款模式）
- 上游测试使用 lest 框架：`test/byte.t.cpp` / `test/byte-main.t.cpp`

## 依赖
- 无任何第三方依赖（仅标准库）

## 首轮 Adapt / 本地验证
- 待执行：clang++ 编译 test_package smoke test + 上游 CTest 测试套件
### 对话 #1（R04 finish 就绪复核）
- 核验三条外部基线（goaccess ncurses-headers.tar.gz、scudo-malloc .manifest-complete/.progress-closed）tracked/哈希一致/未暂存。
- 清理范围审计：archives/b/byte-lite/0.3.0/** 下 __pycache__/*.pyc 零命中，无缓存需清理。
- 补齐 test-report.md、.staging-verified、packaging/ 就绪标记，重跑完整 finish 至退出码 0。
---

**编译结束**: 2026-08-30 19:17
**最终状态**: built
