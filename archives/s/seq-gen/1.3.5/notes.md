# seq-gen 1.3.5 适配笔记

## 编译环境

- 构建系统: makefile（`source/Makefile`，无 configure / CMake / meson，无 install 目标）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK clang 15.0.4（`--target=aarch64-linux-ohos --sysroot=<OHOS SDK>/sysroot`，经 `/Users/metyierzhen/ohos-toolchain/clang` 包装）
- 目标: ohos-aarch64（本机验证用 conan profile `ohos-local`，与 `ci/conan/profiles/ohos-aarch64` 同源配置，仅工具链路径指向本机 SDK）
- 状态: built（本地 `conan create` / `conan-verify` 全绿，未 `conan upload`，R29 不伪造 published）

## 编译步骤

```bash
# 1) 依赖预检（W0 / R35）
#    seq-gen 无任何 conan 依赖（纯 C + libm），无需 conan download 预检；
#    制品仓查重：conan.cnb.cool 搜索 seq-gen -> results=[]（无已发布包）

# 2) 初始化 + 语言预检（R47）
python3 scripts/ohc-run.py init-build seq-gen 1.3.5 \
    --url=https://github.com/rambaut/Seq-Gen/archive/refs/tags/v1.3.5.tar.gz
python3 scripts/ohc-run.py lang-preflight seq-gen 1.3.5 --src "$BUILD_SRC_DIR"
#    -> 语言匹配: task=cpp, detected=c（c<->cpp 兼容族），源文件 11 个（c:11），主体占比 100%

# 3) 交叉编译（配方 build() 内的实际命令，CLINKER 取自 conan conf，R33）
make -j1 CLINKER="<conf tools.build:compiler_executables.c>" \
     CFLAGS="-O2 -Wno-incompatible-library-redeclaration"

# 4) 配方验证（G1-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify seq-gen 1.3.5 --profile ohos-local
```

产物: `bin/seq-gen`（110 KB 级 ELF64 AArch64 PIE，sha256 构建日志留档）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CLINKER = cc` / `CFLAGS = -O3` | 上游假设 UNIX 桌面机自带 cc；鸿蒙 worker 的 `cc` 不是 Conan 提供的编译器 | make 命令行整体覆盖 `CLINKER`/`CFLAGS`（命令行赋值优先于 makefile 赋值），取值来自 `tools.build:compiler_executables`，不用 shell 环境变量（R33） |
| 2 | tarball 里带一个预编译的 `source/seq-gen`（Mach-O arm64，147848 字节） | 上游把 macOS 构建产物提交进了仓库；留着可能被 make 视为"目标已最新"而跳过重链接，更会把外来 ABI 产物打进包 | `build()` 先 `os.remove()` 该文件再 make；`ohos_abi_check.py` A6 用魔数 + sha256 双锚点验证包内产物不是它 |
| 3 | Makefile 没有 install 目标 | 上游 README 只说"二进制会生成在 source 目录" | `package()` 用 conan `copy()` 自行落 `bin/`，并 `chmod 0o755` |
| 4 | `package()` 阶段退出码 127 | OHOS 签名工具按先例取 `/data/service/hnp/bin/llvm-objcopy`（设备路径），本机不存在 | 签名块加 `os.path.isfile()` 门控：worker 上照常执行 remove-section + binary-sign-tool；本机交叉编译时新链产物本无 `.codesign`，跳过是安全的（E077 语义不变） |
| 5 | 本机无法执行交叉产物，`can_run()` 却返回 True | `conan-verify --profile ohos-local` 把同一份 OHOS profile 同时当 `-pr:h` 与 `-pr:b`，conan 判定非交叉 | test_package 沿用 libidl2 0.8.14 / secpwgen 1.3 先例：`can_run()` 之外再判 `user.build:flex_bison_native`（只有本机 `ohos-local` profile 设置），本机跳过运行时用例，真实 worker 照跑全套 |
| 6 | CI L2 smoke test 会 warn | seq-gen 只实现 `-h`（退出码 0），不实现 GNU 风格 `--version`/`--help`（两者退出码 1） | 不改上游 CLI 语义；PR 补充说明中如实记录 L2 为非阻塞 warn，功能测试 F1-F20 在 worker 上实跑覆盖真实可执行性 |

## 源码修改

无。上游源码是可移植 ISO C（仅用 stdio/stdlib/math/time/string/ctype/limits），
无平台 ifdef、无 socket/线程/特权调用，不需要任何补丁（`patches_applied: []`）。
所有适配点都在配方层：编译器注入、预编译产物清理、手动安装、OHOS 签名。

## 上游测试清点（R51 三步法）

### 第一步：清点上游原始测试

官方 tarball `v1.3.5.tar.gz`（sha256 `abd03af0239f02786ddfdddf02ce6b655e544e3bdcf864091538735fe1ce58ae`，tag 指向 commit `d52dc23c3b387be5df5ab9a5131150682163b663`）共 35 个文件：

```
.gitignore  README.md  manual.md
documentation/(Seq-Gen.Manual.html、Using_Seq-Gen_with_PAUP、Version_History、icon.gif)
examples/(example.tree、heterogeneity.tree、recombinant.tree)
source/(Makefile + 11 个 .c + 10 个 .h + 一个预编译二进制 seq-gen)
test/ZIKV_100.newick.trees
```

- `test/` 只有一个 3.0 MB 的 Newick 树**数据文件**，没有任何测试脚本、断言或驱动
- `source/Makefile` 的目标只有 `dummy/clean/default/all/seq-gen/debug`，**无 `check` / `test` 目标**
- 无 gtest / criterion / check / CUnit 等测试框架绑定，无 `*_test.c` / `test_*.c` 源文件，仓库无 CI 配置

**上游测试用例数 = 0**（单元 0 / 集成 0 / 其他 0）。

### 第二步：可运行环境实际运行

上游无测试可运行（0 项）。适配后补全 29 项中：
- 鸿蒙特有 A1-A9 已在**打包产物**上实跑（conan create 的 test_package 阶段，9/9 PASS）
- 功能 F1-F20 的断言逻辑已在**本机原生构建**上 20/20 实跑验证（用于证明断言本身正确）
- F1-F20 的设备端实跑由 `can_run()` 门控，在真实 HarmonyOS worker 上执行（本机无法运行 aarch64-linux-ohos ELF，日志中已如实标注跳过原因）

### 第三步：适配后测试清单（29 项独立检查项）

功能补全 20 项（`test_package/test_seq_gen.sh`，上游 0 -> 新增 20）：

| 项 | 命令 | 断言 |
|----|------|------|
| F1 | `seq-gen -h` | 退出码 0 |
| F2 | `seq-gen -h` | stderr 含 `Usage: seq-gen` 概要 |
| F3 | `seq-gen -h` | banner 含 `Version 1.3.5` |
| F4 | `seq-gen`（无参） | rc!=0 且 stderr 有 usage（防"无法执行"被误判为"正确拒绝"） |
| F5 | `seq-gen -m BOGUS -l 10 t.tree` | rc!=0 且 stderr 有 `Unknown Model: BOGUS` |
| F6 | `-m HKY -l 60 -z 12345 t4.tree` | 恰好 4 条记录（taxa 数来自树） |
| F7 | 同上 | 每条序列长度 == 60（`-l` 生效） |
| F8 | 同上 | 核苷酸字母表仅 ACGT |
| F9 | 同种子跑两次 | 输出逐字节相同（种子确定性） |
| F10 | 换种子 `-z 4242` | 输出与 F9 不同（RNG 真的变了） |
| F11 | `-op` | PHYLIP 头为 ` 4 60` |
| F12 | `-op` | 主体每分类一行、Taxon1 行存在 |
| F13 | `-or` | relaxed PHYLIP：Taxon1 行单空格分隔且序列长 60 |
| F14 | `-on` | 首行 `#NEXUS` |
| F15 | `-m WAG -l 30` | 4 条记录，氨基酸字母表 ⊆ ARNDCQEGHILKMFPSTWYV |
| F16 | `-n 2` | 2 数据集 x 4 分类 = 8 条记录 |
| F17 | `-a 0.5 -g 4` | gamma 速率异质下仍 4 x 60 |
| F18 | 双树文件 | 2 x 3 分类 = 6 条记录 |
| F19 | `-of`（可写 cwd） | 生成 `output_1.fasta` 且含 4 条记录 |
| F20 | `-wa` | 额外输出内部节点祖先序列（记录数 > 4） |

鸿蒙特有 9 项（rule12，N=9 >= 1；`test_package/ohos_abi_check.py`，纯 Python 解析 ELF，不依赖 worker 上的 readelf）：

| 项 | 针对的鸿蒙适配点 | 断言 |
|----|-----------------|------|
| A1 | 目标架构 | ELF64 小端且 `e_machine == EM_AARCH64(183)`（Makefile 硬编码 `cc` 已被配方注入的编译器覆盖） |
| A2 | 工具链/sysroot | `PT_INTERP == /lib/ld-musl-aarch64.so.1`（鸿蒙 musl 加载器；glibc 产物会是 `ld-linux-aarch64.so.1`） |
| A3 | 平台标识段 | 存在 `.note.ohos.ident` 且 owner == `OHOS`（knowledge/operations/harmonyos-specifics.md：不可删除） |
| A4 | libc 归属 | `DT_NEEDED` 含未版本化 `libc.so`，无 `libc.so.6`/`libm.so.6`/宿主库 |
| A5 | libm 折叠 | exp/log/pow/cos/sin 为 UND 且无版本化 libm（OHOS SDK sysroot 只有 88 字节 libm.a 桩） |
| A6 | 预编译产物清理 | 包内产物不是 tarball 里那个 Mach-O arm64（魔数 + sha256 a8c0c6ea... 双锚点） |
| A7 | RPATH 泄漏 | 无 `DT_RPATH`/`DT_RUNPATH`（构建机路径在设备上不存在） |
| A8 | HNP 加固基线 | PIE(ET_DYN+DF_1_PIE) + PT_GNU_RELRO + NX stack + BIND_NOW 同时成立 |
| A9 | glibc 版本化 | 无 `.gnu.version_r` GLIBC_* 需求且无 GNU `.note.ABI-tag` |

> 未断言 `.codesign` 的有无：按 E077，配方先 remove-section 再由 binary-sign-tool 重签，
> 该段在 worker 上存在、在本机不存在，任一方向断言都依赖宿主，不可复现，故不纳入。

`test_package` 本身不自动算鸿蒙特有测试：上表 9 项都是独立、可复核、
明确针对鸿蒙工具链/ABI/打包差异的检查项，已按统一口径计入。

## 验证结果

### 1. conan-verify（G1-G4 + L2/L4/L5）

```
$ python3 scripts/ohc-run.py conan-verify seq-gen 1.3.5 --profile ohos-local
  G1: PASS   配方完整性（含 test_package/ 与 test_package/MANIFEST.yml）
  G2: PASS   conan create 干净构建成功（seq-gen/1.3.5@ohpcd/stable）
  G3: PASS   系统同名库隔离（R26）：无 lib/ 目录，纯可执行包，无冲突
  G4: PASS   产物完整性
  L2/L4/L5: PASS（本机未取到 cache 路径而跳过；L4 安全属性已由 A8 在打包产物上实测）
✅ 配方验证通过: seq-gen 1.3.5
```

### 2. build() + package() 阶段实测

```
make -j1 CLINKER="/Users/metyierzhen/ohos-toolchain/clang" \
     CFLAGS="-O2 -Wno-incompatible-library-redeclaration"
-> 11 个 .o + 链接 -lm 全部成功，无错误（eigen.c 的 cexp 重声明为上游既有 warning）
WARN: removing upstream prebuilt binary shipped in the tarball (Mach-O arm64)
```

### 3. test_package 层（打包产物上实跑）

```
[PASS] A1..A9（9/9）
OHOS_ABI_CHECK={"discovered": 9, "passed": 9, "failed": 0}
cross-building: an aarch64-linux-ohos ELF cannot execute on this host,
so the 20 test_seq_gen.sh runtime cases are skipped here and are
exercised on the HarmonyOS CI worker
```

### 4. 功能断言逻辑验证（本机原生构建，非鸿蒙证据）

```
$ sh test_seq_gen.sh /private/tmp/seqgen-native
SEQ_GEN_FUNCTIONAL={"discovered": 20, "passed": 20, "failed": 0}
```

用途：证明 F1-F20 的断言本身正确（期望值全部来自实测）；
设备端实跑仍以 HarmonyOS CI worker 结果为准，不用本机原生冒充。

### 5. 负向对照（防恒真断言 / L1e 口径）

```
$ python3 ohos_abi_check.py --binary <tarball 里的 Mach-O 预编译产物>
[FAIL] A0_artifact_readable: not an ELF file (magic b'\xcf\xfa\xed\xfe')  -> rc=1
$ python3 ohos_abi_check.py --binary <不存在的路径>
[FAIL] A0_artifact_readable: [Errno 2] No such file or directory          -> rc=1
$ sh test_seq_gen.sh <空目录>
FAIL: seq-gen not found in <dir>                                          -> rc=1
$ sh test_seq_gen.sh <OHOS 交叉产物目录>（本机无法执行）
SEQ_GEN_FUNCTIONAL={"discovered": 20, "passed": 3, "failed": 17}          -> rc=1
```

## 已知限制

- 上游不实现 `--version`/`--help`（GNU 风格），CI L2 smoke test 会给非阻塞 warn；
  真实可执行性由 F1-F20 在 worker 上覆盖
- `.codesign` 签名只在具备 HNP 工具的 HarmonyOS worker 上发生（E077），
  本机交叉产物无该段，A9 改为断言无 glibc 版本化以保持跨宿主可复现
- `test/ZIKV_100.newick.trees`（上游唯一"测试数据"）未打包；
  功能测试使用上游 `examples/example.tree` 的同内容树（自包含，不依赖源码树）
---

**编译结束**: 2026-09-27 14:07
**最终状态**: built

## 远程 CI 终态（2026-09-27 回填）

- PR: #13208（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13208）
- 远程 HarmonyOS CI: **通过**，构建 **#62717**，worker `OpenHarmonyPCDeveloper-CI-021`
- `Conan test_package: 通过`、`L0 门禁（结构完整性）: 通过`、`L1 门禁（测试执行验证）: 通过`
- 构建步骤 `worker_preparation / worker-prep / git-clone / checkout-pr / conan-setup /
  conan-build-test / cleanup` 全部 ✅（`conan-build-test` 1m37s）
- 完整日志: https://ohpcd.atomgit.com/ci?id=62717
- atomgit-bot AI 检视: PR 创建后 30 分钟窗口内未产出任何意见（仅两条"进行中"占位评论），
  P0/P1 = 0，无待闭环评审意见；如需重跑可 `/ai review force`
- SKILL_FEEDBACK 终稿已随分支提交（d93760d0cf）；result.json 终态 success
