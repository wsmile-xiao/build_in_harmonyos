# lsp-test-fw

## 简介

lsp-test-fw 是 [lsp-plugins](https://github.com/lsp-plugins) 项目的测试框架，
提供 utest（单元测试）/ ptest（性能测试）/ mtest（手动测试）/ init（初始化钩子）
四个子系统的注册、分发与执行能力，以及带对齐边界标记的 ByteBuffer/FloatBuffer
断言辅助类。lsp-plugins 生态各库（lsp-common-lib、lsp-r3d-* 等）均基于本框架
编写上游测试。

## OHOS 适配

- **构建系统**：上游自研 make 系统（`make config` → `make` → `make install`）
- **适配方式**：零补丁。上游 make 按 `uname -s` 探测平台，OpenHarmony PC 返回
  "HarmonyOS"（上游不识别，落入 Unknown 分支），配方构建时显式传 `PLATFORM=Linux`。
  OHOS aarch64 目标（-march=armv8-a + asimd）与上游 Linux 路径一致，
  源码无 `#ifdef` 平台差异需要修改。
- **交付物**：`liblsp-test-fw-1.0.35.{so,a}` + `pkgconfig/lsp-test-fw.pc` +
  头文件 `include/lsp-plug.in/test-fw/**`；`shared=False` 时仅交付静态库，
  `shared=True` 时对 .so 执行 OHOS 代码签名（动态库加载前置条件）。
- **版本**：1.0.35（上游 tag）

## 依赖

无（零外部依赖，lsp-plugins 生态最底层测试框架）。

## 功能验证

```bash
# 上游测试（四子系统）
./.build/target/lsp-test-fw/lsp-test-fw-test utest   # exit 0
./.build/target/lsp-test-fw/lsp-test-fw-test ptest   # exit 0
./.build/target/lsp-test-fw/lsp-test-fw-test mtest   # exit 0
./.build/target/lsp-test-fw/lsp-test-fw-test init     # exit 0
```

本地验证记录：`conan create` static/shared 双变体通过；`conan-verify` G0–G4 全
PASS；`ci/conan/build_and_test.sh` 本地 CI 模拟 L0/L1/L4/L5 均 pass。

## 参考

- 上游仓库: https://github.com/lsp-plugins/lsp-test-fw
- License: LGPL-3.0-or-later
