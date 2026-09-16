# conan-verify 补充验证 — dbskkd-cdb 3（制品 dbskkd-cdb/3.00）

**日期**: 2026-09-11
**设备**: HarmonyOS PC aarch64（os=OHOS 6.0，Conan 2.29.1，clang 15.0.4）
**本文档的时效口径**: 本文覆盖两轮：① 首次适配轮（用例 26）；② **规则 12 修复轮**（用例 31，
新增 5 项鸿蒙特有平台检查），②为本 PR 的最终状态。文中标注「首次适配轮」的数值属历史记录，
不再是当前口径。

**证据文件形态**: 原始 `conan-create.log` / `w3-local-ci.log` **不随 PR 提交**（仓库审查规则 19
把 `*.log` 列为 PR 禁止文件）；其关键行区间已逐字摘录（非全文）进同目录的 `conan-create-report.md` 与
`w3-local-ci-report.md`，两者均为②轮的日志，`test_package summary` 行均为
`TOTAL=31 PASS=31 FAIL=0`。原始日志留存任务私有目录并在报告中给出 sha256 与复核命令。

## 为什么要人工补测

`ohc-run.py conan-verify dbskkd-cdb 3` 的 G0/G1/G2/G3 实跑 PASS，但报告里
G4/L2/L4/L5 四行是 `⏭️ 跳过（无 cache 路径）`（工具文案缺陷：同一行左侧仍打印
`✅ PASS`，按 workflow 第 7.2 节以跳过行为准）：

```
## G3: ✅ PASS
  ⚠️ 无法获取 conan cache 路径（可能 G2 未通过）
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID
## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

根因不是 G2 失败——G2 实跑 PASS，`reports/conan-create-report.md`（原 `conan-create.log` 关键行区间的
逐字摘录，非全文；原始日志按规则 19 不入库）里有完整的干净构建与测试记录
（`Apply patch` 1 条、`RUN: make` 1 条、`test_package summary: TOTAL=31 PASS=31 FAIL=0`）。
真正的触发点是 **引用版本形态不一致**：conan-verify 以 `--version 3` 组装出
`dbskkd-cdb/3@ohpcd/stable`，而配方用 `set_version()` 把制品版本归一化为上游发布号，
实际创建的制品是 `dbskkd-cdb/3.00@ohpcd/stable`（`conan list "dbskkd-cdb/*"` 只返回
`dbskkd-cdb/3.00@ohpcd/stable`）。工具按 `3` 去解析 package_id 自然拿不到，于是整组
L2/L4/L5 走「无 cache 路径」分支。

这与 workflow 第 7.2/17 节登记的「G4 定位失败」同族（`conan list --format=json`
顶层键带 `@user/channel` 而内部 ref 不带），但此处叠加了 set_version 归一化，
属于**必然命中**而非偶发。以下四项按固定口径人工补测，全部针对 G2 实际产出的包目录。

## G4 产物完整性

包目录定位（glob，分片目录名每轮重建）：`ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dbskk*/p`

```
bin/dbskkd-cdb
licenses/LICENSE
conaninfo.txt
conanmanifest.txt
```

与 `package_info()` 互相印证：`bindirs = ["bin"]` 有真实可执行产物；
`libdirs = []`、`includedirs = []`、`libs = []` 与包内无 `lib/`、无 `include/` 一致
（纯可执行包，G3 亦打印「无 lib/ 目录」语义的跳过）。

```bash
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dbskk*/p | head -1)
find "$PKG" -type f | sed "s|$PKG/||" | sort
```

## L2 消费者实际行为

真实命令（不是 `--version` 探测——本包没有版本开关，退出码 0 与协议应答才是行为证据）：

```bash
printf '2' | "$PKG/bin/dbskkd-cdb" <SKK-JISYO.test.cdb>   # -> "dbskkd-cdb-3.00 " rc=0
printf '1かんじ ' | "$PKG/bin/dbskkd-cdb" <SKK-JISYO.test.cdb>  # -> "1/漢字/" rc=0
printf '1not-in-dict ' | "$PKG/bin/dbskkd-cdb" <SKK-JISYO.test.cdb>  # -> "4not-in-dict" rc=0
```

字节级结果见 `reports/conan-create-report.md` 的 `test_package summary` 行：
**TOTAL=31 PASS=31 FAIL=0**（26 个消费者协议/夹具用例 + 5 个鸿蒙特有平台检查）。
注意 CI/W3 侧的 `L2 smoke` 只试 `--version`/`--help` 并要求 rc=0，对本包（无参数即
进入协议循环、无参数时等 stdin）恒失败并整组记 `L2_RESULT=skip`，故此处以协议行为为准。

## 鸿蒙特有平台检查（规则 12 修复轮新增）

`test_package/fixtures/ohos_platform_check.py` 对**随包二进制**做 5 项 OHOS 平台专属断言，
全部用纯 Python 解析 ELF（不依赖 `readelf`，设备与 CI worker 行为一致），5 个 `CHECK` 行
并入 `test.sh` 同一套 `[ok]/[fail]` 计数：

| 用例 | 断言 | 实测值 |
| --- | --- | --- |
| `ohos_elf_aarch64_pie` | ELF64 / AArch64 / `ET_DYN`(PIE) | `type=3, machine=183` |
| `ohos_elf_codesign` | 非空 `.codesign` 段（OHOS 加载器只执行带有效签名的 ELF，E077） | `.codesign` size=16384 |
| `ohos_elf_hardening` | `PT_GNU_STACK` 无 `PF_X`(NX) + `PT_GNU_RELRO` + `DF_BIND_NOW` + `DF_1_PIE` | `nx=True relro=True bind_now=True df_1_pie=True` |
| `ohos_elf_relocatable` | `DT_NEEDED` 恰为 `[libc.so]`、无路径分隔符、无 `DT_RPATH`/`DT_RUNPATH` 指向构建或缓存目录 | `DT_NEEDED=['libc.so']`，无 RPATH/RUNPATH |
| `ohos_runs_minimal_env` | 仅 `PATH` 的最小环境 + 词典取自调用方可写目录即可正确应答 | `rc=0`、`stdout='dbskkd-cdb-3.00 '` |

## L4 安全属性

```bash
readelf -h  "$PKG/bin/dbskkd-cdb"   # Class: ELF64  Type: DYN (Position-Independent Executable file)
readelf -lW "$PKG/bin/dbskkd-cdb"   # GNU_STACK RW（不可执行栈 = NX）、GNU_RELRO 存在
readelf -dW "$PKG/bin/dbskkd-cdb"   # FLAGS: BIND_NOW、FLAGS_1: NOW PIE、DT_NEEDED 仅 libc.so
```

四项判据（DYN + `GNU_STACK RW` + `GNU_RELRO` + `BIND_NOW`/`PIE`）全部满足，与上表
`ohos_elf_hardening`/`ohos_elf_relocatable` 两项自动检查互为印证。
产物含 hnp lld 的 `.codesign` 自签段（`readelf -SW` 可见），因此配方与上游一致地
**不做 strip**：链接后任何字节改写都会使签名失效，内核以 `Operation not permitted`
拒绝 exec。

## L5 产物基线与跨轮稳定性

判据用两条稳定聚合，且在包目录内以**相对路径**计算（分片目录名每轮重建，
带绝对路径的写法必然漂移）：

| 指标 | 值 |
| --- | --- |
| `bin/dbskkd-cdb` sha256 | `62a2e57cbaa80714cdb68c56bc50e8bf526a2e07d2543ec5d7bce08cd7f5dfaa` |
| 包内容聚合（排除 `conaninfo.txt`/`conanmanifest.txt`） | `5df15dae0b1a6cdb595664ccc9dec4f4cba4edde5083dfd1d8b71ff93d53698d` |
| `licenses/` 聚合 | `f3ab06fd36066c403adced0b3dcce13db8521a6da6e133247a7d0cd34789bc16` |
| 包许可证 sha256 | `5b1bece3b74ab7a2d15c1522cae9c57ca41947a02fc35c5bad3d96185b8c3c4b` |

```bash
cd "$PKG" && find . -type f | sed 's|^\./||' \
  | grep -v -E '^(conaninfo|conanmanifest)\.txt$' | sort | xargs sha256sum | sha256sum
cd "$PKG" && find ./licenses -type f | sort | xargs sha256sum | sha256sum
```

**可复现性判别**（先判别再给基线）：每轮都先真清缓存（`conan remove
"dbskkd-cdb/*@*" -c`、`conan remove "dbskkd-cdb/*" -c`、`rm -rf "$CONAN_HOME"/p/*/dbskk*`，
并用 `p/cache.sqlite3` 的 `recipes`/`packages` 两表对包名回查为空确认），再各跑一次
`conan create`。全程（含规则 12 修复轮）`bin/dbskkd-cdb` 的 sha256 稳定为
`62a2e57c…df5dfaa`、包内容聚合稳定为 `5df15dae…d53698d`（分片目录名每轮不同而聚合值相同，
正是「聚合命令必须在包目录内以相对路径计算」的效果），**无不可复现项**，基线对整个包成立。
各轮日志均含 `Calling build()` 与 1 条 `RUN: make`，都是干净构建轮而非缓存命中。

> 说明：`conan-verify`/W3 在构建前会临时把 `conandata.yml` 的 `sources.url` 改写成镜像列表
> （结束后还原），因此日志中出现的 recipe revision 会随镜像注入形态变化，**不是**配方内容的
> 稳定指纹；配方内容的稳定性以 git 的对象哈希与 `git diff <SHA>..HEAD -- <构建输入路径>`
> 输出为空为准（见「构建输入不变性」一节）。

## L1e 破坏性反向验证（本地等价执行）

```bash
# 桩产物：把包产物换成只应答 '2' 的最小 ELF
bash test.sh <桩目录> <cdb tools bin 目录>
# -> rc=1（本轮 TOTAL=27 PASS=11 FAIL=16；首次适配轮为 TOTAL=22 PASS=6 FAIL=16）
bash test.sh <产物被整体移走的目录> <cdb tools bin 目录>
# -> rc=1，[fail] dbskkd-cdb: binary missing in package
```

测试确实依赖被测包产物（而非 PATH 上的同名命令）：全部 31 个用例（含 5 个平台检查）
都从被测包 `bin/` 取二进制。桩产物轮的用例总数小于 31，是因为桩缺少真实会话所需的应答、
部分用例在读取阶段即失败，属失败路径的正常表现，不作为通过证据。

## 构建输入不变性

本 PR 后续提交只改 `reports/`、`commands.json`、包级/版本级 `manifest.yaml`、`notes.md`、
`README.md` 等非构建输入文件；**规则 12 修复轮改了 `test_package/`**（新增
`fixtures/ohos_platform_check.py` 并接线 `test.sh`），因此本文件所述 31 用例的证据日志
已在同一轮内重跑并覆盖提交，不存在「日志与实际测试不一致」的情况。

自证命令（对任意两个待比较的 SHA）：

```bash
git diff <SHA_A>..<SHA_B> -- archives/d/dbskkd-cdb/3/conanfile.py archives/d/dbskkd-cdb/3/conandata.yml \
  archives/d/dbskkd-cdb/3/patches archives/d/dbskkd-cdb/3/test_package
```

## 结论

G2 采信轮为干净构建轮；L2/L4/L5/G4 四组判据由本文件人工补齐并全部满足要求，其中
L4 的两条属性已由 `test_package` 内的 `ohos_elf_hardening`/`ohos_elf_relocatable`
两项自动检查持续覆盖。工具的跳过行为按显式 SKIPPED 对待，不计入自动通过。
