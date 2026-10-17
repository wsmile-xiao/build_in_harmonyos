# findlib (ocamlfind) 1.9.8 适配笔记

**日期**: 2026-09-22
**状态**: ✅ built
**平台**: HarmonyOS PC (aarch64, musl, Clang 15.0.4)
**工具链**: `tool_requires ocaml/4.14.1.1.4`

## 概述

findlib 是 OCaml 的库管理器，提供 `ocamlfind` CLI：解析包的 META 文件、
把 `-package X` 翻译成编译/链接参数并驱动 OCaml 编译器。

构建系统为项目自带的 autoconf 风格 `configure`（非标准 autotools，无
Makefile.am）+ GNU Make：

```
configure → make all → make opt → make install
```

产物：`bin/ocamlfind`（安装时优先选用原生 ELF `ocamlfind_opt`）、
`lib/ocaml/findlib/` 下的 findlib.cma/.cmxa/.cmxs 与各 META 模板。

## 关键适配点（1 个补丁，3 类问题）

全部集中在 `patches/0001-configure.patch`（+45/-7，OHOS 守卫均以 `$OCAMLRUN`
为条件，非 OHOS 平台不设置该变量时行为与上游完全一致）。

### 1. OCaml 字节码工具的 shebang 失效 + hmmac 拒绝执行脚本

- 现象：`configure` 在 "Testing DLLs..." / "Testing whether ppxopt..." /
  "Detecting compiler arguments" 阶段报
  `.../bin/ocaml: No such file or directory`、
  `tools/extract_args/extract_args: No such file or directory`
- 根因：这些工具是 shebang 指向**编译期嵌入的 ocamlrun 绝对路径**的字节码
  脚本。conan 包 store 迁移后该路径失效（ENOENT）；且 OHOS hmmac 本就拒绝
  直接执行 shebang 脚本（E253 坑 1）。
- 方案：新增 `ocaml_run()` 辅助函数，当 `$OCAMLRUN` 已设置时改为
  `"$OCAMLRUN" "$@"` 显式调用，覆盖 configure 中 3 处字节码调用点
  （ocaml 顶层 ×2、extract_args ×1）。

### 2. 字节码运行缺少 C stubs 搜索路径

- 现象：显式 ocamlrun 调用后报 `Cannot load required shared library dllunix`
- 根因：字节码链接/运行需加载 `lib/ocaml/stublibs/dllunix.so` 等 C stubs，
  但 stublibs 不在默认加载路径；shebang 失效导致无法自动定位。
  该缺失同时使 configure 的两处能力探测（DLL 支持、ppxopt）误判为「不支持」。
- 方案：新增 `ocaml_setup_runenv()`，在 stdlib 目录确定后立即把
  `stublibs` 追加到 `CAML_LD_LIBRARY_PATH` 并 export；同时把该值写进
  `Makefile.config`（供 `make all/opt` 子进程继承）。

### 3. OHOS 无 GNU install(1)

- 现象：`make install` 报 `/bin/sh: install: inaccessible or not found`
- 根因：OHOS 为 toybox/BusyBox 环境，无 GNU coreutils 的 `install`；
  configure 硬编码 `INSTALLDIR = install -d` / `INSTALLFILE = install -c`。
- 方案：configure 探测 `install` 是否存在，缺失时回退为上游注释中已给出的
  可移植组合 `mkdir -p` / `cp`（与 BSD 环境的官方建议一致）。

## 验证证据

| 阶段 | 命令 | 结果 |
|------|------|------|
| configure | `/bin/sh ./configure ...` | EXIT=0，生成 Makefile.config |
| 编译（字节码） | `make all` | EXIT=0 |
| 编译（原生） | `make opt` | EXIT=0（含 findlib*.cmxs 共享库） |
| 安装到 staging | `make install DESTDIR=$TEST_PREFIX` | EXIT=0，48 个文件 |
| 上游集成测试 | `./itest` | 编译 4/4 通过；执行阶段平台豁免（见下） |
| 等价功能验证 | `ocamlfind ocamlopt -linkall -linkpkg -package <lib>` | unix/str/threads/bigarray 4/4 编译+运行通过 |
| 端到端 | 见 `reports/test-summary.md` | 成功 |

日志：`reports/configure.log`、`reports/make-all.log`、`reports/make-opt.log`、
`reports/make-install.log`、`reports/itest.log`、`reports/test-summary.md`

## 平台限制（已豁免）

上游 `itest` 对每个库执行 `ocamlfind ocamlc -linkall -linkpkg -custom ...`
并运行产物、断言输出 `OK`。OHOS 下：

- 阶段 1（ocamlfind 解析 META 并驱动编译）**4/4 全部成功**——证明 findlib
  核心功能正确；
- 阶段 2（执行 `-custom` 产物）受平台限制：hmmac 拦截，重签名后 OCaml
  custom runtime 报 `no bytecode file specified`（runtime 在 musl aarch64
  上误把自身 ELF 当作字节码参数）。

该限制来自 **OCaml 运行时自身**，非 findlib 缺陷。按
`docs/TEST_QUALITY_SPEC.md §3.3` 在 `test_package/MANIFEST.yml` 的
`upstream_test_results.fail_analysis` 中如实申报，并以原生 `ocamlopt` 路径
（itest 的同等语义）完成 4/4 等价验证。

## 后续建议

- `ocamlfind` 安装产物为原生 ELF，可直接执行，无 shebang 依赖
- 下游若需在 OHOS 编译 OCaml 代码，可 `tool_requires("findlib/1.9.8")`，
  并确保 `CAML_LD_LIBRARY_PATH` 指向 ocaml 包的 `lib/ocaml/stublibs`
- OCaml `-custom` 模式在 OHOS 的运行时缺陷可考虑反馈至 ocaml/4.14.1.1.4 配方
---

**编译结束**: 2026-09-22 13:07
**最终状态**: built
