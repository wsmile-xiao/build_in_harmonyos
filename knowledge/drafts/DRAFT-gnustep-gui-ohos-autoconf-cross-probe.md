# DRAFT-gnustep-gui-ohos-autoconf-cross-probe - OHOS CI must not execute unsigned autoconf conftest probes

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-29
> **Source event**: gnustep-gui 0.32.0 HarmonyOS PC adaptation, PR #7095 CI #34102

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

GNUstep GUI 在 HarmonyOS PC worker 上运行 `configure`，且 Conan
`AutotoolsToolchain` 生成的 `--build` 与 `--host` 都落到
`<cpu>-unknown-linux-ohos`。这会让 autoconf 认为当前是 native build。

典型日志如下：

```text
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking whether the C compiler works... yes
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
```

## 根因

HarmonyOS CI worker 能编译临时 C 程序，但 autoconf native 模式会继续执行
`conftest` 或 `a.out`。这些临时可执行文件没有进入正式签名/安装链路，在 worker
运行域内会被拒绝执行。由于 `build == host`，autoconf 没有进入
`cross_compiling=yes` 分支，最终在运行探针处停止。

## 推荐方法

在 OHOS 分支中，在调用 configure 前过滤 Conan 生成的 `--build`、`--host` 和
`--target` 参数，然后显式写入一组不同的 build/host triplet：

```sh
--build=<cpu>-unknown-linux-gnu \
--host=<cpu>-unknown-linux-ohos \
--target=<cpu>-unknown-linux-ohos \
ac_cv_prog_cc_works=yes
```

这会让 autoconf 进入交叉编译路径，跳过必须运行临时可执行文件的探针；同时
`host/target` 仍然保留 OHOS triplet，避免把产物误标成 GNU/Linux。

## 与已有知识的差异

- E011/HMDFS 类问题处理的是临时目录权限或 `umask 077`。
- 本草稿处理的是 autoconf 运行编译探针导致的签名/沙箱失败；即使 compiler works
  已经通过，也会在 `checking whether we are cross compiling` 阶段暴露。

## 禁止做法

- 不要只追加第二组 `--build/--host`，要先过滤已生成的等值 triplet，避免解析顺序不确定。
- 不要把该处理扩散到 Linux 分支；Linux native build 应保持正常运行探针。
- 不要用关闭 AppKit 功能的方式掩盖 configure 的运行探针问题。

## 证据来源

- `archives/g/gnustep-gui/0.32.0/conanfile.py`
- `archives/g/gnustep-gui/0.32.0/notes.md`
- PR #7095 CI #34102 `conan-build-test` configure 日志
