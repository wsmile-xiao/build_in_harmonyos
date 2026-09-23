# E429 — OHOS SDK 缺 llvm-ranlib：纯 CMake 项目显式指定 CMAKE_RANLIB 引用 hnp/bin 预置 softlink

- terkait类: ohos, cmake, toolchain, archive
- 严重度: 2 (medium)
- 来源: box2d 3.1.1 适配（R01, pc1-18），2026-09-06 实测

## 问题 / 错误签名

- `Error running link command: no such file or directory`（cmake 运行 cmake_link_script 执行 link.txt 时）
- OHOS SDK 26.0.0.18 的 `native/llvm/bin/` 只提供 `llvm-ar`、`llvm-nm`，**无 `llvm-ranlib`**，
  CMake 自动推断 RANLIB 为同目录不存在的 `llvm-ranlib`，静态库归档的 ranlib 步骤失败
- llvm-ar 单独运行正常（`llvm-ar qc lib.a *.o` 可成功产出归档），但 `llvm-ranlib` 路径不可访问

## 根因

OHOS SDK 工具链目录不完整（缺 llvm-ranlib multi-call 别名）。但 `/data/service/hnp/bin/llvm-ranlib`
是 SDK 预置的 multi-call 软链（指向 llvm-ar，按 argv[0] 分发），可直接引用。

## 修复

CMake 配置时显式指定：

```bash
cmake -S . -B build \
  -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
  -DCMAKE_AR=/data/service/hnp/bin/llvm-ar \
  -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib
```

不复制、不伪造 SDK 文件；仅引用 SDK 已预置的 softlink（与 E385 的 wrapper/overlay 方案不同，
纯 CMake 顶层项目只需配置参数即可）。

## 验证（box2d 3.1.1 实测）

- 配置: exit 0；全量构建: exit 0（libbox2d.a/libshared.a/libenkiTS.a/test 全部产出）
- 上游测试: 9/9 通过；鸿蒙专项测试: PASS；test_package 消费者测试: 1/1 Passed
- 验证命令: `test ! -x native/llvm/bin/llvm-ranlib; test -x /data/service/hnp/bin/llvm-ranlib`
  → 前者不存在（确证问题）、后者存在（确证修复路径）

## 适用边界

- 适用: 纯 CMake 顶层项目（非 Cargo build.rs/cmake crate 子构建）构建静态库
- 不适用/另见: Cargo 子构建场景 → E385（wrapper + toolchain overlay）；autotools 场景 → E012（AR/RANLIB 环境变量）

## 关系

- similar_to: E385（Cargo 子构建 llvm-ranlib 缺失方案）
- 无 conflict / prerequisite