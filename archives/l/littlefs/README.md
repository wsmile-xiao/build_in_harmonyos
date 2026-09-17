# littlefs

A little fail-safe filesystem designed for microcontrollers.

- 上游：https://github.com/littlefs-project/littlefs
- 版本：2.11.2（归档内）
- 许可：BSD-3-Clause
- 构建系统：纯 Makefile（`make` 默认目标即 `liblfs.a`，无 CMake/configure）
- 依赖：无（零依赖库）
- 适配状态：published（OHOS aarch64，clang 15）
- 特点：嵌入式掉电安全文件系统；官方自研 TOML 测试框架（194 用例 /
  11606 permutations 全量通过，含 28741 次掉电场景）