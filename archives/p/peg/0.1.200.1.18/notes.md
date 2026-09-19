# peg 0.1.200.1.18 适配笔记

## 版本说明

- Conan 版本 `0.1.200.1.18` 对应 Debian/Ubuntu 的 `0.1.20+really0.1.18`（`+really` 规范化为点号）。
- 其源码内容即上游 Ian Piumarta peg **0.1.18**（2016-07-22）：
  `https://www.piumarta.com/software/peg/peg-0.1.18.tar.gz`
  sha256 `20193bdd673fc7487a38937e297fff08aa73751b633a086ac28c3b34890f9084`。
- 已有归档 `peg/0.1.19` 覆盖了 0.1.19；本版本补齐 0.1.18 内容线，便于依赖该语义的下游复现。
- 构建系统与 0.1.19 一致：纯 Makefile（无 configure），产物为 `peg`、`leg` 两个可执行文件，零外部依赖，无补丁。

## 构建信息

- 构建系统：纯 Makefile（无 configure）
- 源码：官方 peg 0.1.18（sha256 见 conandata.yml）
- 产物：peg、leg 两个可执行文件
- 外部依赖：无
- 补丁：无

## 上游测试清点

- `make test`（examples/）：11 个用例（test/rule/accept/wc/dc/dcv/calc/basic/localpeg/localleg/erract），
  逐一“生成 C → 编译 → 管道输入 → diff .ref”。
- `make check`（自举一致性）：check-peg / check-leg 两项。
  与 0.1.19 不同，0.1.18 自带预生成文件与语法文件自洽，`make check` 应作为真实构建门禁（不忽略错误）。
- 合计：13 项（11 集成 + 2 自举）。

## 适配要点

- conf 取值：`tools.build:compiler_executables` 须整体取 dict 再 `.get("c")`，
  子键直取会抛 ConanException（沿用 0.1.19 经验）。
- make 必须以 `cwd=self.source_folder` 执行（conan build() 默认 cwd 是 build_folder）。
- make check/test 显式传 CC（CI 环境无 `cc`，examples 子 make 编译示例需要 clang）。
- test_package 沿用 0.1.19 的 `test.sh`：`peg -V` / `leg -V` + 从 PEG 语法生成 C 代码并断言 `yyparse`，
  实质执行被测二进制，满足 R34。

## 验证结果（待真机回填）

- conan create：待 HMBS 真机预检
- make test：待真机实测（预期 11/11）
- make check：待真机实测（预期 2/2）
- test_package：待真机实测

---

**编写日期**: 2026-09-18
**最终状态**: built
