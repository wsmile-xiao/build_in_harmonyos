- **三方库名称**：ol（Otus Lisp）
- **上游版本**：2.7
- **上游仓库地址**：https://github.com/yuriy-chumak/ol
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E188（OHOS 无 coreutils `install`）、E077（strip 后 ELF 丢 `.codesign`，内核拒绝执行）、E140（`uname -s` 返回 HarmonyOS 导致平台分支不匹配）、E543（libc++ 遮蔽，草稿）、E383（共享库缺 `DT_SONAME`）、DRAFT-cd-hit-4.8.1-make-conan-recipe（make 命令行变量覆盖 makefile 的 `+=`）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 78 | `make language-tests` 62（tests/*.scm 61 + tests/*.bin 1）+ `make ffi-tests` 16（tests/ffi/tier-1 7 + tier-2 9）；其中 `tests/fasl-binary.bin` 上游默认不执行，见下方说明 |
| 集成测试 | 0 | 上游无独立集成测试套件 |
| 其他测试 | 133 | Rosetta Code 示例 112（tests/rosettacode/**）+ 参考手册代码块 21（doc/reference/*.md） |
| **合计** | **211** | 一个测试文件计一个用例（清点所得）；实际运行 210 例，每例跑 debug + release 两个 olvm = 420 次 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 78 | 不变 | 上游清单原样执行，无跳过、无裁剪 |
| 集成测试 | 0 | 不变 | — |
| 其他测试 | 133 | 不变 | Rosetta Code 112 + 参考手册代码块 21，原样执行 |
| 鸿蒙特有测试 | 3 | 新增 | `test_package` 消费者用例：`embed_test`（C 消费者，`<ol/ol.h>` 嵌入 API 5 断言）、`harness.scm`（`bin/ol` 解释器 7 断言）、`olvm --version` |
| **合计** | **214** | **+3** | 上游合计 211 + 鸿蒙特有测试 3 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **修改的测试文件**：`tests/rosettacode/object_serialization.scm`
   - **修改原因**：该用例把序列化结果硬编码写到 `/tmp/object.bin`，而鸿蒙的 `/tmp` 是 root 属主只读挂载（`touch /tmp/x` 报 `Read-only file system`），`fasl-save` 必然失败、`fasl-load` 返回 `#false`，用例在鸿蒙上恒失败。
   - **修改内容**：落盘路径由 `/tmp/object.bin` 改为构建树内相对路径 `tmp/object.bin`（`patches/0002-tests-rosettacode-object_serialization.scm.patch`，+3/-2）。用例语义与 `.ok` 期望输出完全不变，无平台宏（`platform_only: False`、`guard: none`）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：210/210（100%）
- 上游未运行用例：1 个，`tests/fasl-binary.bin` 属**上游默认不执行**——上游 `extras/check.mk` 的 `%.bin.ok` 规则被整段注释，`tmp/check.log`（378 条执行记录）无它，日志里只有名字行没有结果行；该例既非 PASS 也非本包 SKIP，单列申报（清点合计仍为 211）
- 新增测试用例通过率：3/3（100%）

## 补充说明

- 消费者与产物证据见 `archives/o/ol/2.7/reports/`：`conan-create-log.md`（`conan create` 逐字日志，干净轮）、`upstream-check-log.md`（上游 211 例逐字日志，末行 `UPSTREAM_MAKE_CHECK_RC=0`）、`conan-verify-supplement.md`（工具对 G4/L2/L4/L5 报「跳过（无 cache 路径）」后的人工补测：产物清单 280 项 ↔ `bindirs`/`libdirs`/`includedirs`、包内 `bin/ol` 与 `bin/olvm` 实测运行、`llvm-readelf` 核 PIE/NX/RELRO/`.codesign`、两轮独立构建逐字节一致的 sha256 基线）。
- 本包为全新包：本地 preflight 会把 API 形态的 `owner:branch` head 当成 `git diff main...<source>`（PF0），并要求包级 `README.md`/`manifest.yaml`/`commands.json` 落在 5 段版本目录（PF9），两处对全新包均为确定性误报，故以 `--no-preflight` 建 PR；本地等价核对：① 改动只有 `archives/o/ol/` 一个包目录、无框架文件；② 无源码归档、无二进制入库；③ `test_package/` 真实存在且已在 `conan create` 内实跑编译型消费者；④ `conanfile.py` 无 `requires`，无依赖门槛。
- 补丁 2 个（`patches/0001-GNUmakefile.patch`、`patches/0002-tests-rosettacode-object_serialization.scm.patch`）：前者给 `libol.so` 链接补 `-Wl,-soname,libol.so`（上游 `-shared` 未设 SONAME，产出的 `.so` 无 `DT_SONAME`，CLI 质量门禁 L5a 报「下游链接器无法按 SONAME 寻址」；修后 `llvm-readelf -dW` 见 `SONAME Library soname: [libol.so]`），后者见上节说明。
- 上游测试编排参数（与串行 `make check` 用例集合完全一致，不抽样、不减变体）：四组 `language-tests`/`rosettacode-tests`/`ffi-tests`/`check-reference` **各复制一份已构建源码树、在副本里并行执行**（各组自身仍 `-j1`），逐组落盘后按固定顺序拼接为 `upstream-check.log`；独立副本是为消除四个并发 make 实例对共享中间产物（`tmp/`、`ol`/`olvm`、`tests/ffi/src.inc`）的竞态（CI #46152 上 ffi 组曾因共享树 rc=2 失败）。命令行同时预置 `HAVE_SOCKETS/HAVE_DLOPEN/HAVE_SECCOMP/HAVE_MEMFD_CREATE=1`（`configure.mk` 用 `?=`），省掉每次子 make 的 clang 特性探测。墙钟由 ~25-30 分钟降到 ~10 分钟，以满足 CI 的 `conan create` 3600s 上限（串行时 CI #45856 实测 `TIMED OUT after 3600s`）。
- OHOS 适配要点（详见 `archives/o/ol/2.7/notes.md`）：上游 `make install` 依赖 coreutils 的 `install(1)`（OHOS 未提供）→ 配方 `package()` 按上游 install 布局自行落盘；`bin/olvm` 经上游 `strip` 后丢失 `.codesign`、内核以 `Operation not permitted` 拒绝执行（rc=126）→ 用 `binary-sign-tool` 重新自签名（`libol.so` 保持 hnp clang 自带链接器签名，不重签）；鸿蒙 `uname -s` 返回 `HarmonyOS`，会跳过上游 `ifeq ($(UNAME),Linux)` 分支、丢掉 `-Xlinker --export-dynamic`，使运行期 FFI 取不到 `OLVM_ffi` → 构建显式传 `UNAME=Linux`；运行期 `OL_HOME` 由 `package_info()` 的 runenv/buildenv 导出为 `<包>/lib/ol`，包可重定位。
- W4 独立审计（返修后复审轮）：verdict=pass，P0=0、P1=0、P2=1、P3=2；被审 SHA `949d58cf96e8192a5ff6b42b6893a9a04bbd80f5`，与 `git rev-parse HEAD` 人工核对一致。上一轮审计的 P1（上游用例申报数与逐字证据不符：`tests/fasl-binary.bin` 上游默认不执行却被计为通过）已按实测口径改正为「清点 211 / 实际运行 210/210 / 未运行 1 例单列」，并把配方校验升级为「测试名行 ↔ 结果行」逐项配对、未申报的未执行用例直接让 `conan create` 失败；上一轮 P2/P3（版本级 manifest 的补丁描述矛盾、license 写法、签名工具缺失静默跳过、知识引用歧义）均已修。本轮残留 P2 为逐字留档的行尾空行丢失（已修，三份留档自述 sha256 与代码块内容现已逐字节吻合）、P3 为注释位置与仓库层知识取号碰撞存量，均非阻断。审计输入按该 SHA 生成、审计期间工作区干净；其后 delta 仅 `reports/conan-create-log.md` 一个证据文件，不涉及构建输入与门禁物料。
- T1 声明行：W4 审计 verdict=pass（P0/P1=0）对 `f24499c2e9cf1c6e30ac9eb3e059bea4a014be6b` 生效；其后 delta 仅含 `archives/o/ol/2.7/reports/conan-verify-supplement.md`、`archives/o/ol/2.7/reports/pr-body.md`，不涉及构建输入与门禁物料，已按文档一致性自检。
