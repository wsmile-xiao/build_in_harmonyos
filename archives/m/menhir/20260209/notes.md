# menhir 20260209 适配笔记

## 编译环境
- 构建系统: Dune（release profile，自举构建）
- 编译日期: 2026-10-04
- 编译器: clang/clang++（OCaml 工具链来自 Conan 制品仓）
- 状态: built

## 编译步骤

1. 源码: 官方 GitLab archive（tag 20260209），sha256 校验通过
2. 工具链: `tool_requires("ocaml/4.14.1.1.4")`、`tool_requires("dune/3.17.0")`
   （OHOS 系统镜像无 OCaml；registry 已有二者）
3. 构建: `dune build -p menhirLib,menhirSdk,menhirCST,menhirGLR,menhir --profile release @install`
4. 打包: 复制 `_build/install/default`（bin/menhir + lib/menhirLib 等）到包目录
5. 消费者测试: test_package/test.sh（生成/编译/运行解析器 + 负向用例）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | init-build 把 benchmarks/ 误当源码根（dune 仓库根无 Makefile/configure 等标记） | 仓库工具嵌套源码提升启发式的标记集合不含 dune-project | 用工具原语重建 .orig/.work 并在根放置本地 marker，禁止改动框架脚本 |
| 2 | ocamlc/ocamlopt 找不到 stdlib | Conan 缓存重定位后编译器内置路径失效 | 构建前导出 `OCAMLLIB=<ocaml_prefix>/lib/ocaml` |
| 3 | OHOS 拒绝 shebang 脚本直执行 | 平台安全策略 | test_package 由 conanfile 以 `/bin/sh test.sh` 显式调用 |
| 4 | 表后端消费者链接 menhirLib 失败风险 | MenhirLib 无 findlib 环境 | `ocamlopt -I <prefix>/lib/menhirLib <prefix>/lib/menhirLib/menhirLib.cmxa <模块...>`（OCaml 原生链接要求归档先于使用它的模块） |

## 源码修改

无补丁；上游 tag 20260209 原样构建。

## 依赖版本

- OCaml: 4.14.1.1.4（Conan 制品仓，tool_requires）
- Dune: 3.17.0（Conan 制品仓，tool_requires）
- clang: 15.0.4（OHOS SDK）

## 验证结果

- `conan-verify` G0–G4 全部 PASS（干净 `conan create` + test_package）
- test_package 消费者测试 13/13 PASS（版本、code/table 后端生成、ocamlopt 编译链接、
  运行结果 7/42、两条负向：非法输入 exit 2 / 未声明 token 文法被拒绝）
- 本地 CI 门禁（与平台同脚本）L0/L1/L1e/L2/L4/L5 全部 pass，退出码 0
- 上游 `demos` 测试：10/12 通过；2 例失败为上游 tag 自身不一致（calc-inspection
  `.exp` 期望 `require_unreleased` vs 生成 `require_20260209`；calc-GLR 引用 `fix`
  vs vendored 库公开名 `vendored_fix`），与 OHOS 适配无关，详见 reports/test-report.md
- 设备无 GNU `as`、制品仓 ocaml 内嵌 CI worker clang 路径：本机验证使用
  `ohos-aarch64-device` profile 的本地工具覆盖（local/bin/as、ccwrap、OCAMLPARAM），
  归档配方本身不依赖这些覆盖

**编译结束**: 2026-10-04
**最终状态**: built
