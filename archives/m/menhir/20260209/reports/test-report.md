# menhir 20260209 — 适配验证报告

## 基本信息

- 任务: menhir #8796（平台任务 #8796，分支 `feat/menhir-20260209`）
- 官方源码: https://gitlab.inria.fr/fpottier/menhir/-/archive/20260209/archive.tar.gz
- sha256: `69f0414b047d1d5b3507eb8277cd328a60d430bdff51de912b47adb2c25de4f3`
  （与 opam `menhir.20260209` 元数据同源归档）
- 构建方式: Dune release profile，自举构建（driver/stage1 由 ocamlyacc 生成 →
  driver/stage2 将 stage1 可执行文件绑定为 `menhir` 生成最终解析器与可执行文件）
- 构建依赖（Conan 制品仓 tool_requires）: `ocaml/4.14.1.1.4`、`dune/3.17.0`
- 适配路径: 路线 A（基础适配；无源码补丁，上游 tag 原样构建）

## 1. conan-verify（G0–G4）

- [PASS] `python3 scripts/ohc-run.py conan-verify menhir 20260209 --profile ohos-aarch64-device`
  返回 0；G0/G1/G2/G3/G4 全部 PASS
- G2 干净 `conan create`：下载官方归档（校验 sha256）→ `dune build -p
  menhirLib,menhirSdk,menhirCST,menhirGLR,menhir --profile release @install` → 打包 →
  test_package 执行（13/13）
- 报告留存: 本地工作区 `reports/conan-verify-report.md`（未入仓，属 raw 证据）；
  原始日志留存于构建工作区 `~/work/kasumizawa-miyuu/menhir-evidence/`（`conan-verify-7.log`）

## 2. 消费者测试（test_package，鸿蒙特有测试）

命令（conan 自动化执行）: `/bin/sh test_package/test.sh <menhir_prefix> <ocaml_prefix>`

| # | 断言 | 结果 |
|---|------|------|
| 1 | `menhir --version` 退出码 0 | PASS |
| 2 | 版本串包含 `20260209` | PASS |
| 3 | `menhir --code` 生成解析器退出码 0 | PASS |
| 4 | 生成 `test.ml` + `test.mli` | PASS |
| 5 | `ocamlopt` 编译 code 后端解析器 + 驱动 | PASS |
| 6 | 运行 `calc '1+2+4'` 退出码 0 | PASS |
| 7 | 输出 `7` | PASS |
| 8 | 非法输入 `1+` 触发 `Parser.Error`（exit 2，负向） | PASS |
| 9 | 未声明 token 的文法生成期被拒绝（负向） | PASS |
| 10 | `menhir --table` 生成解析器退出码 0 | PASS |
| 11 | 经 `-I lib/menhirLib` + `menhirLib.cmxa` 链接表后端 | PASS |
| 12 | 运行 `calc_table '20+22'` 退出码 0 | PASS |
| 13 | 输出 `42` | PASS |

**13/13 PASS**（本次运行原始日志: `~/work/kasumizawa-miyuu/menhir-evidence/` 内 quick-run 与 CI 日志中的测试段）

## 3. 上游测试（R51 三步法）

清点：上游测试设施为 `demos/`（`make -C demos test`；12 个 demo，各自 `dune build
--force --display short @test`，对生成产物与运行输出逐字节 diff `.exp`）。

实机运行（未改动的 `20260209` 源码树 + 本包安装的 menhir/menhirLib/CST/SDK/GLR）：

- 通过 **10/12**：`calc`, `calc-alias`, `calc-ast`, `calc-incremental`, `calc-mini`,
  `calc-new-syntax`, `calc-param`, `calc-syntax-errors`, `calc-two`, `generate-printers`
- 失败 2 例，均为**上游 tag 自身不一致**（同一未改动源码在完整工作区可复现，与 OHOS
  适配无关；逐项原因如下）：
  - `calc-inspection`：`.exp` 期望 `MenhirLib.StaticVersion.require_unreleased`，
    而该 tag 构建实际生成 `require_20260209`（上游开发版/发布版版本串不一致；
    上游 release 校验脚本 `check-tarball.sh` 只跑 `dune build @install`，不跑 demos）
  - `calc-GLR`：demo 的 dune 引用库 `fix`，而 vendored 库公开名为 `vendored_fix`
    （同仓 `base/dune` 使用的是 `vendored_fix`；上游 demo 未随改名更新）
- 逐 demo 结果与原始日志: `~/work/kasumizawa-miyuu/menhir-evidence/upstream-demos-per-demo.txt`、
  `demo-*.log`

## 4. 本地 CI 门禁（与平台 CI 同一脚本）

```
CONAN_PROFILE=ohos-aarch64-device CI_PACKAGES=archives/m/menhir/20260209 \
  zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

结果：退出码 0；L0（质量门禁，含 L0i/L0j/L0k/L0m）、L1（test_package 被执行）、
L1e（破坏性负向：移走 lib 后测试确实失败）、L2（`menhir --version` smoke）、
L4（补丁危险函数扫描：无补丁）、L5（bin/ 产物基线）全部 pass。
原始日志: `~/work/kasumizawa-miyuu/menhir-evidence/w3-local-ci.log`

## 5. 设备环境差异（如实记录，不进入归档）

本机共享真机镜像缺少 GNU binutils `as`；制品仓 `ocaml/4.14.1.1.4` 内嵌了 CI worker
路径 `/data/service/hnp/bin/clang`（本机不存在），且用 `-cc` 覆盖 C 编译器时 OCaml
驱动会丢失 `-shared`/`-Wl,-E` 链接参数。为完成**本机**门禁，在本地 profile
`ohos-aarch64-device` 增加纯设备侧工具覆盖（归档主体、仓库框架文件均未改动）：

- profile `[buildenv]`/`[runenv]`：PATH 前置 `~/work/kasumizawa-miyuu/local/bin`；
  `OCAMLPARAM=_,cc=<local ccwrap>`
- `local/bin/as`：`exec "${CC:-clang}" -c "$@"`（供 OCaml 原生汇编）
- `local/bin/ccwrap`：恢复 `-cc` 覆盖时丢失的 `-shared`（cmxs）与 `-Wl,-E`（可执行）

平台 CI runner 具备 `/data/service/hnp` worker 工具链与 GNU `as`，本归档配方为
无补丁 stock 构建，**不依赖**上述本机覆盖。

## 6. 结论

- 归档 `archives/m/menhir/20260209/`（conanfile/conandata/manifest/notes/test_package）
  在本机通过全部门禁；消费者测试 13/13；上游 demos 10/12（2 例为上游自身不一致）。
- 路线 A（【积分赛】）：真实适配、无伪造、无密钥/绝对路径泄漏。
