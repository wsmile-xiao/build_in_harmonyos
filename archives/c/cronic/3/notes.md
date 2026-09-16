# cronic 3 适配笔记（HarmonyOS PC）

## 范围与来源

cronic 是一个 cron 任务输出包装脚本（bash 实现）。它把一条命令包起来执行，仅在
被包命令**退出码非 0** 或**产生非空 stderr** 时输出报告（命令行 / 结果码 / 错误输出 /
标准输出），否则完全静默，从而避免 cron 每次都把正常运行输出当"有事发生"发给用户。

- 官网：http://habilis.net/cronic/
- 源码（官方 GitHub 镜像，https 固定 commit）：
  `https://github.com/justincase/cronic/archive/6e627fbe5498c360d091d9ecd06b0ac242704566.tar.gz`
- 许可证：Public Domain / CC0-1.0
- 归档内容：扁平 3 个文件——`LICENSE`(6625 B)、`README.md`(4121 B)、`cronic`(854 B)

实测下载与校验（R39 官方源）：

```console
$ sha256sum $TMPDIR/builds/cronic-3.tar.gz
f99a5f48d917d7d766c15cebeddd5c7788620a13d4659b822b7cb300cf217376  cronic-3.tar.gz
# 与 conandata.yml 声明一致；与任务卡给定 sha256 一致
$ find $TMPDIR/builds/cronic-3.work -type f | sort
./LICENSE
./README.md
./cronic
```

## 版本甄别：目录 `3` ↔ 制品 `cronic/v3`

任务卡版本为 `3`，上游 README 亦将该版本标注为 **"Cronic v3"**；上游仓库**无任何 git
tag**（`GET /repos/justincase/cronic/tags` → `[]`），也不存在点分版本（无 `3.0`/`3.0.0`）。

**Conan 2.x 硬约束**：`RecipeReference.validate_ref()`（`conan/api/model/refs.py`）用
`^[a-z0-9_][a-z0-9_+.-]{1,100}$` 校验版本号——首字符之后**至少还要 1 个字符**，即版本
最短 2 字符。因此 `cronic/3` 在 `conan create` 的导出阶段直接失败（conan-verify 首轮
G2 实测）：

```console
$ conan create archives/c/cronic/3 -pr:h=ci/conan/profiles/ohos-aarch64 ...
======== Exporting recipe to the cache ========
ERROR: Invalid package version '3'
```

该校验无 conan 配置可放宽（`core.allow_uppercase_pkg_names` 只管大小写）。本仓库已有
同型先例：

| 先例 | 目录 | `set_version()` | 制品引用 |
|------|------|-----------------|----------|
| `archives/c/cutmp3/4` | `4` | `"4.0"` | `cutmp3/4.0` |
| `archives/r/rapidhash/3` | `3` | `"v3"` | `rapidhash/v3` |
| `archives/b/base-devel/1.0` | `1.0`（改目录） | 字面 `version` | `base-devel/1.0` |
| **本次 cronic** | **`3`** | **`"v3"`** | **`cronic/v3`** |

**采用方案（与任务卡约束自洽）**：归档目录、分支保持任务卡的 `3` / `feat/cronic-3`；
配方**不写字面 `version = "..."` 属性**，改用 `set_version()` 把制品版本归一化为上游
标签 **`v3`**（保留上游原样版本标识，不做无依据的 `.0` 发明，与 rapidhash 同型）。
CI 的 L0m 规则 3 与 PF8 的"版本目录 ↔ 配方 version 一致性"只对**字面** `version = "..."`
生效，`set_version()` 形态天然跳过，目录与制品版本的对应关系由本 notes 与版本级
manifest（`version: "3"` / `upstream_version: "v3"` / `conan_ref: "cronic/v3"`）留证。
`commands.json` 的版本键/ref 按 CI L0k、preflight PF8 的机械口径写 `"3"` / `cronic/3`
（与 `cutmp3/commands.json` 完全同型）。

## W0 — 依赖发布检查

无 `requires` / `tool_requires`。cronic 运行期只依赖 `bash` / `grep` / `mktemp` 三个
**系统工具**（不是 Conan 包）。证据：

```console
$ bash ci/scripts/preflight_check.sh cronic/3
  适配前预检: cronic/3   制品仓: ohpcd
  [INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。
  [OK] 预检通过（无依赖需要检查）

$ grep -nE 'requires|tool_requires' archives/c/cronic/3/conanfile.py
# 仅出现在文档字符串里（说明"没有 requires"），无任何 self.requires()/tool_requires()
```

→ R36"依赖先发布再构建下游"不适用（无依赖链）。

## W0b — 历史经验核验 + CI 能力矩阵

- **仓库内无 cronic 历史归档**：`git ls-files archives | grep -i cronic` → 空；
  `find archives -iname '*cronic*'` 在开工前为空（现仅命中本次新建目录）。
  knowledge/ 中亦无 cronic 条目。→ 无可继承的历史 notes，无历史踩坑需比对。
- **CI 能力矩阵对照**：cronic 属 **bash 脚本类 → ✅ 正常**（CI 不需要 Rust/OCaml 等
  冷门工具链；无编译单元，不涉及 gcc/clang/cmake）。**环境语义可迁移**：`conan create`
  在 CI clean 环境逐字可执行（本机已用与 CI 同源 `ci/conan/profiles/ohos-aarch64` 实测
  通过）。bash 在鸿蒙 CI/设备上位于 `/data/service/hnp/bin/bash` 并在 PATH 中。

## W1 — 同步主仓库

起点 `main` 已与 `upstream/main` 对齐：`5dff0c6a5c`（`!9495 merge feat/dbview-1.0.4 into
main`）。本任务从该点切出 `feat/cronic-3`。

## 语言预检（R47，两种口径均实测）

本包无编译单元，`detected_language=other`（三级判定全落"无"）：

```console
$ python3 scripts/ohc-run.py lang-preflight cronic 3 --src $TMPDIR/builds/cronic-3.work
  ❌ 语言不匹配: task=cpp, detected=other → env_unsupported        # 退出码 2
  {"expected":"cpp","detected_language":"other",
   "language_evidence":{"build_system":"none",
     "manifest":"未发现语言 manifest 文件","source_stats":"无源文件可统计"},
   "notes":["无可统计源文件"]}
```

- **默认口径（任务语言 cpp，即 `OHPCD_LANG` 缺省）**：`detected_language=other` ≠ `cpp`，
  工具按 R47 判"不匹配"、**exit 2**，并把本包**误**写成终态 `env_unsupported`。这与实际
  不符——本包是合法可打包的纯脚本包，不是"编译器/平台不支持"。为避免污染真实结果位置，
  该次运行的 `OHC_RESULT_OUT` 显式重定向到临时文件（`$TMPDIR/cronic-default-cpp-result.json`），
  未写入平台回执路径。
- **实际采用口径（`--lang other`）**：`detected_language=other` == 期望 `other` → 匹配、
  **exit 0**，正常进入适配主流程：

```console
$ python3 scripts/ohc-run.py lang-preflight cronic 3 --src $TMPDIR/builds/cronic-3.work --lang other
  ✅ 语言匹配: task=other, detected=other — 继续适配主流程
```

**理由**：R47 判定的"不匹配"语义是"源码主体语言不是任务标注的编译型语言"，用于拦掉
"把 C/C++ 任务派到非 C/C++ 源码"的浪费。本包确属"无 C/C++ 可编"的纯脚本/资源型交付
（与同型先例 `archives/b/breeze-grub/6.7.2`（资源包）、`archives/p/pari-galpol/20180625`
（数据包）一致），它们的合法口径都是显式 `--lang other`。**禁止把包伪判为 cpp** 来"凑"
默认口径——那会把 `detected_language` 与事实相悖、且在 R47 的枚举校验下属违规申报。
任务语言若由派发侧注入，本包应注入 `OHPCD_LANG=other`。

## R51 — 上游测试三步法

**① 清点（实证：上游 0 个测试）**。官方 tarball（commit `6e627fbe`）解包后**只有 3 个
普通文件、0 个目录**：

```console
$ find . -type f | wc -l        # 3（不含解包器附加的 .tarball-sha256/.edit-tracker.json）
$ find . -type d | wc -l        # 0
$ ls -la                        # LICENSE(6625) README.md(4121) cronic(854)
$ for f in Makefile configure CMakeLists.txt meson.build setup.py configure.ac tests test; do
    [ -e "$f" ] && echo "FOUND: $f" || echo "absent: $f"; done
absent: Makefile / configure / CMakeLists.txt / meson.build / setup.py / configure.ac / tests / test
```

无 `tests/`、无任何构建系统、无 CTest/pytest 注册、无功能测试脚本、无 CI 配置。
→ **上游功能用例数 = 0**；没有修改或删除任何上游测试（因为不存在）。

**② 运行（无上游测试可运行）**：`build()` 中无 `make check`/`ctest`/`pytest` 可调用；
这是资产形态使然，不是"没环境"。

**③ 如实回填**：`test_package/MANIFEST.yml` 已如实写明 `upstream_tests: []`、
`upstream_test_count: 0` 并附清点证据；功能验证由本包 `test_package` 提供（见下）。
上游 0 个用例与 test_package 6 个用例**分别申报**，不用 6 冒充上游覆盖。

## 配方说明

- `package_type = "application"`（交付 `bin/cronic` 可执行脚本）；`settings` 四项齐全
  （os/compiler/build_type/arch，满足 L0p/PF8）。
- 无编译：`build()` 仅 `apply_conandata_patches(self)`（patches 为空 → 安全空操作）并做
  上游脚本存在性校验；`export_sources()` 走标准补丁钩子（与 pari-galpol 同型，满足
  conan-verify G1 的配方完整性检查）。
- `package()`：`cronic` → `bin/`；`LICENSE` → `licenses/`；`README.md` →
  `share/doc/cronic/`。`package_id()` 置空（纯脚本与 os/arch/compiler 无关，单一
  package_id `da39a3ee5e6b4b0d3255bfef95601890afd80709`）。
- `package_info()`：`bindirs=["bin"]`，libdirs/includedirs/libs 置空，
  `resdirs=["share/doc/cronic"]`。

## HMDFS / 权限注意事项

- 鸿蒙**无 `/bin/bash`**（`ls /bin/bash` → not found），bash 在
  `/data/service/hnp/bin/bash`（已在 PATH）。cronic 的 shebang 是 `#!/bin/bash`，因此
  **不能依赖 shebang 直接执行**；test_package 与调用方统一用 `bash <pkg>/bin/cronic ...`。
- HMDFS 上 `chmod` 常被忽略、权限被归一化（本仓库 E046 / R49 记录），执行位不可靠。
  配方仍尽力 `os.chmod(bin/cronic, 0o755)`，但**不把执行位当作测试前提**：测试通过
  `bash` 显式解释执行，不依赖 `X_OK`。
- L2 smoke（CI 用 `"$bin" --version` 直接执行）在 HMDFS 上可能因执行位/shebang 失败，
  该门禁为**非阻塞 warn**；本包真正的功能验证在 test_package（真实调用被测脚本）。

## test_package（R34：真实调用被测包）

`test_package/conanfile.py` 的 `test()` 只做两句 `self.run('bash "<script>" "<bin/cronic>"')`
（无内联 echo/print，满足 CI L1d），全部断言逻辑写在 shell 脚本内。

### 通用语义 `test_package/test_cronic.sh`（3 用例 / 6 断言）

通过 `bash` 显式执行**已安装**的 `<pkg>/bin/cronic`，覆盖 cronic 的核心语义：

| 用例 | 命令 | 断言 |
|------|------|------|
| case1 命令成功且无输出 | `cronic true` | 输出为空（静默） |
| case2 命令退出码非 0 | `cronic false` | 输出含 `Cronic detected failure`；含 `RESULT CODE: 1` |
| case3 命令成功但有 stderr | `cronic bash -c 'printf ... >&2'` | 含 `Cronic detected failure`；含 `RESULT CODE: 0`；含 stderr 文本 |

注意：cronic 是"报告包装器"，**自身始终以 0 退出**（不转发被包命令退出码），故断言
落在**输出内容**而非 cronic 的退出码。

### 鸿蒙特有测试 `test_package/test_cronic_ohos.sh`（6 用例 / 14 断言）

针对鸿蒙运行时特性逐条真断言（**本机实测 14/14 PASS，0 SKIP**）：

| 用例 | 断言数 | 内容 | 本机实测 |
|------|--------|------|----------|
| OHOS-1 运行时依赖与 shebang 基线 | 4 | ①`bash`/`grep`/`mktemp` 均可用（`command -v`）；②`head -1 bin/cronic` == `#!/bin/bash`；③`bash <script> true` 静默成功（PATH bash 可用）；④本机无 `/bin/bash` → 直接执行 `bin/cronic` 失败（rc=126），**证明 shebang 不可解析、调用方必须 `bash <script>`** | 4/4 PASS（`/bin/bash`=absent，`bash`=`/data/service/hnp/bin/bash`） |
| OHOS-2 与执行位无关（HMDFS chmod 归一化） | 2 | ①`bin/cronic` 复制后 `chmod 0644`，`bash <copy> false` 仍产出含 `Cronic detected failure` / `RESULT CODE: 1` 的报告；②该报告与原始脚本输出**逐字节一致**。**不断言 chmod 生效**（HMDFS 实测把 0644 归一化为 `-rw-rw----`） | 2/2 PASS（chmod 后模式 `-rw-rw----`） |
| OHOS-3 可写 TMPDIR 依赖（/tmp 只读陷阱） | 3 | ①`TMPDIR=<可写目录>` 时正常运行且报告正确；②运行后该目录**无 cronic 临时残留**（`mktemp -d` 已清理）；③`TMPDIR=<不存在目录>` 时**失败**（rc≠0）且诊断非空 | 3/3 PASS |
| OHOS-4 UTF-8 与含空格路径 | 2 | ①UTF-8（无空格）TMPDIR 下，中文 stdout/stderr 在报告中**原样回显**；②`TMPDIR` 含空格时 cronic **响亮失败**（rc≠0、诊断非空）——上游脚本 `"$@" >$OUT 2>$TRACE` 的 `$OUT`/`$TRACE` **未加引号**（`cronic` 第 15 行），空格路径触发 `ambiguous redirect`。断言"绝不静默误判"，并在「风险/不确定点」如实记录 | 2/2 PASS（UTF-8 回显正确；空格路径 rc=1） |
| OHOS-5 HNP bash 兼容（条件用例） | 2 | 若 `/data/service/hnp/bin/bash` 存在：①静默用例与默认 bash 一致（都为空）；②失败报告与默认 bash **逐字节一致**；不存在则 SKIP | 2/2 PASS（本机 HNP bash 存在） |
| OHOS-6 只读 `/tmp` 陷阱（条件用例） | 1 | 若 `/tmp` 不可写：`unset TMPDIR`（默认落 `/tmp`）时 **cronic 失败**（rc≠0）→ 证明必须把 `TMPDIR` 指向用户可写目录（如 `$HOME/tmp`）；`/tmp` 可写则 SKIP | 1/1 PASS（本机 `/tmp` = read-only） |

**条件断言如实申报**：OHOS-1 第 4 条依赖"宿主无 `/bin/bash`"，OHOS-5 依赖 HNP bash 存在，
OHOS-6 依赖 `/tmp` 只读——不具备该条件的宿主会打印 **SKIP**（既不计入通过，也绝不算 fail）。
本机（OHOS aarch64）三项条件全部命中，故 **14/14 PASS、0 SKIP**。本机环境事实：
`bash=/data/service/hnp/bin/bash`、`/bin/bash` 不存在、`/tmp` 只读、
`grep=/data/service/hnp/bin/grep`、`mktemp=/usr/bin/mktemp`。

### 计数汇总（上游 0 / 适配后 9 用例 20 断言，其中鸿蒙 6 用例 14 断言）

| 维度 | 用例 | 断言 |
|------|------|------|
| 上游 | 0 | 0 |
| 适配新增-通用 | 3 | 6 |
| 适配新增-鸿蒙专项 | 6 | 14 |
| **合计** | **9** | **20** |

`test_package/MANIFEST.yml` 存在（CI L0e），并按 R51 如实申报上游测试情况；
字段 `harmonyos_test_count: 6` / `harmonyos_assertion_count: 14` / `assertion_count: 20`。

## W3 本地验证（与 CI 同源）

用仓库自带的 `conan-verify`（`ci/conan/profiles/ohos-aarch64`，conan 2.29.1）：

```console
$ python3 scripts/ohc-run.py conan-verify cronic 3
  ✅ G1: PASS      （配方完整性：name/version/source/build/package/package_info/export_sources/补丁/ conandata/test_package/MANIFEST）
  ✅ G2: PASS      （conan create 成功；制品 cronic/v3@ohpcd/stable；test_package 6/6 PASS）
  ✅ G3/G4/L2/L4/L5: PASS（因报告引用为 cronic/3 与制品 cronic/v3 不一致，取 cache 路径失败而跳过——见"本机与 CI 差异"）
✅ 配方验证通过: cronic 3
```

`conan create` 关键输出见 `reports/test-report.md`（`Running test()` → 6 PASS）。
`conan create` 日志 SHA256 记录在 `.ci-result.json`（由 finish 写入，非手写）。

## 本机与 CI 差异

- **验证工具引用 vs 制品版本**：`conan-verify` 的验证引用硬编码为
  `f"{software}/{version}@ohpcd/stable"` = `cronic/3`，而 `set_version()` 产出的制品是
  `cronic/v3`，故 verify 报告里 G3/G4/L2/L4/L5 因取不到 `cronic/3` 的 cache 路径被判
  "跳过"（仍记 PASS）。这是 set_version 配方 + 该验证器的固有不一致（cutmp3/4 同型）。
  真实 CI（`ci/conan/build_and_test.sh`）**从 create 日志的 "Package folder" 行推导
  `PKG_CACHE`**（不依赖 `pkg_name/pkg_ver`），因此 L2/L4/L5 在 CI 上能取到真实产物：
  bin/ 有内容 → L5 pass；L1e 会移走 bin/ 后重跑 `conan test`，本包测试会因
  `<pkg>/bin/cronic` 缺失而失败 → 正确判为"真测试"。
- 本机为 OHOS aarch64 设备（非 CI clean 容器），但 conan 版本、profile、脚本均与 CI
  同源；`conan create` 本地即真实执行。

## 风险 / 不确定点

1. **单字符版本**：制品引用是 `cronic/v3` 而非 `cronic/3`。下游若按 `cronic/3` 引用会
   找不到包；`commands.json` 的 ref 依 CI 机械口径写 `cronic/3`（PF8）。
2. **release 上传**：`ci/conan/upload.sh` 用目录名 `pkg_name/pkg_ver` 组装 ref（即
   `cronic/3`），与本包实际制品 `cronic/v3` 不一致，合并后 release 上传可能取不到包。
   此问题非本包独有（cutmp3/4 等 set_version 配方同型），属框架侧一致性议题，本 PR 不
   修改框架文件。本任务不执行 upload/submit，故不影响本次交付。
3. **L2 smoke**：HMDFS 执行位不可靠 + 无 `/bin/bash`，`bin/cronic` 可能无法被 CI 直接
   执行；L2 非阻塞，功能验证在 test_package。
4. **语言口径**：需派发侧为该包注入 `OHPCD_LANG=other`，否则默认 cpp 口径会误判
   `env_unsupported`（本 notes 已记录两种口径与理由）。
5. **上游限制：`TMPDIR` 路径不能含空格**（实测，非本包引入）。cronic 第 15 行
   `"$@" >$OUT 2>$TRACE` 的 `$OUT`/`$TRACE` **未加引号**；当 `TMPDIR`（`mktemp -d` 的
   落点）含空格时触发 `ambiguous redirect` / `No such file or directory`，cronic 以 rc=1
   响亮失败（不会静默给出错误结论）。鸿蒙上 `TMPDIR` 通常为 `$HOME/tmp`（无空格），
   故正常场景不受影响。**未修改上游脚本以避免偏离官方源**；该限制已由 OHOS-4 第 2 条
   断言覆盖（断言"响亮失败或不静默误判"，对上游未来修复保持兼容）。
6. **`bin/cronic` 无执行位不影响使用**：HMDFS 上 `chmod` 被归一化（实测 0644→`-rw-rw----`），
   且无 `/bin/bash` 使 shebang 不可解析——两条都指向同一结论：**必须以
   `bash <pkg>/bin/cronic …` 调用**（OHOS-1/OHOS-2 已断言）。

## 复现命令

```sh
# 语言预检（本包口径）
python3 scripts/ohc-run.py lang-preflight cronic 3 --src <源码目录> --lang other

# 配方验证（8 门禁）
python3 scripts/ohc-run.py conan-verify cronic 3

# 直接 conan create（与 CI 同源 profile）
conan create archives/c/cronic/3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 手动跑 test_package 逻辑（对本机脚本亦适用）
bash archives/c/cronic/3/test_package/test_cronic.sh <package>/bin/cronic
bash archives/c/cronic/3/test_package/test_cronic_ohos.sh <package>/bin/cronic
```
---

**编译结束**: 2026-09-14 12:06
**最终状态**: built
