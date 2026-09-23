# peg 0.1.19 适配笔记

## 构建信息

- 构建系统：纯 Makefile（无 configure）
- 源码：官方 peg 0.1.19（sha256 见 conandata.yml）
- 产物：peg、leg 两个可执行文件
- 外部依赖：无
- 补丁：无

## 上游测试清点（R51）

- `make test`（examples/）：11 个用例（test/rule/accept/wc/dc/dcv/calc/basic/localpeg/localleg/erract），
  逐一"生成 C → 编译 → 管道输入 → diff .ref"，OHOS aarch64 实测 11/11 通过。
- `make check`（自举一致性）：check-peg / check-leg 两项。上游 0.1.19 官方 tarball 自携带的
  预生成源码与语法文件不自洽——src/peg.peg-c 由 peg 0.1.18 生成（未随 0.1.19 更新），
  src/leg.c 与 leg.leg 不一致（缺 '\f' 分支），任何平台均复现，属上游打包缺陷而非 OHOS 适配问题。
  适配中保留执行并完整记录差异，但不作为构建断言（conanfile build() 中 ignore_errors=True）；
  生成器功能由 make test 与 test_package 覆盖。

## 适配要点

- conf 取值：`tools.build:compiler_executables` 须整体取 dict 再 `.get("c")`，
  子键直取会抛 ConanException。
- make 必须以 `cwd=self.source_folder` 执行（conan build() 默认 cwd 是 build_folder）。
- make check/test 显式传 CC（CI 环境无 `cc`，examples 子 make 编译示例需要 clang）。

## 验证结果

- conan create：EXIT_CODE=0（~14s）
- make test：11/11；test_package：PASS
- conan-verify：G0-G4 通过；W3 本地 CI pass；W4 审计 pass（P0=0/P1=0）

---

**编译结束**: 2026-09-11
**最终状态**: built
