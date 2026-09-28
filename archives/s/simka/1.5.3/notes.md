# simka 1.5.3 — 一手核验证据（阶段性，未收工）

窗口：主理-74（构建在 B 机）  日期：2026-09-27

## 1. 上游 tag 形态与源件哈希（一手实测）

`git ls-remote --tags https://github.com/GATB/simka` 实测：tag **带 `v` 前缀**，1.5.3 对应
`refs/tags/v1.5.3` → peeled commit `b0d4ec990df0b1dc621a19802f1e0f041b13b4f5`。
（工作区 ttygif 教训是"别假设 v 前缀"，本次实测结论是**该仓确实带 v**。）

GitHub Releases API `repos/GATB/simka/releases` HTTP=200，v1.5.3 发布资产三个：
- `simka-v1.5.3-bin-Darwin.tar.gz`
- `simka-v1.5.3-bin-Linux.tar.gz`
- `simka-v1.5.3-Source.tar.gz`（实测总大小 **18,053,365 B**）

哈希交叉核验（B 机 `sha256sum` 实测）：

| 件 | 大小 | sha256 |
|---|---|---|
| 官方 tag 归档 `https://github.com/GATB/simka/archive/refs/tags/v1.5.3.tar.gz` | 168,163 B | `545182a28430a8149efd709d9be323683c07ab289c5d0e345b67819f845d0628` |
| Debian 池件 `simka_1.5.3.orig.tar.gz`（**仅用于核验，不入 conandata**） | 168,163 B | `545182a28430a8149efd709d9be323683c07ab289c5d0e345b67819f845d0628` |

⇒ **官方上游 tarball 与池件字节数与 sha256 完全同值 ⇒ 认定同一文件**（台账给的池件哈希得到一手复核）。

Debian `simka_1.5.3-10.dsc` 原文摘录（说明为何"必须另找 gatb-core 源"）：
- `Build-Depends: debhelper-compat (= 13), cmake, libgatbcore-dev, zlib1g-dev, libhdf5-dev, libboost-dev, python3-all, dh-sequence-python3, chrpath`
- `Checksums-Sha256: 545182a28430a8149efd709d9be323683c07ab289c5d0e345b67819f845d0628 168163 simka_1.5.3.orig.tar.gz`

即：池件 orig = 官方 tag 归档本体（**不含 submodule 内容**，164 KB），Debian 靠外部
`libgatbcore-dev` 包补 gatb-core。我们不做 Debian 那条路（不自建 gatbcore 发行包），
而是按上游自己的布局把 gatb-core 取进 `thirdparty/gatb-core/`。

## 2. 包形态一手核（**与台账"库"的说法不同**）

`raw.githubusercontent.com/GATB/simka/v1.5.3/CMakeLists.txt`（5,742 B）原文要点：

- `project(simka)` / `cmake_minimum_required(VERSION 2.6)`  ← **CMake 4 会硬失败**
- `SET (GATB_CORE_HOME ${PROJECT_SOURCE_DIR}/thirdparty/gatb-core/gatb-core)`
- `SET (CMAKE_MODULE_PATH ${GATB_CORE_HOME}/cmake)` → `include (GatbCore)`
- `SET (GATB_CORE_EXCLUDE_TOOLS 1)` / `GATB_CORE_EXCLUDE_TESTS 1` / `GATB_CORE_EXCLUDE_EXAMPLES 1`
- `add_definitions (${gatb-core-flags})`、`include_directories(...)`、`file (GLOB_RECURSE ...)`
- `FOREACH (KSIZE ${gatb-core-klist}) configure_file (src/core/SimkaAlgorithmTemplate.cpp.in ...) ENDFOREACH ()`
- **五个 `add_executable`：`simka`、`simkaCountProcess`、`simkaCount`、`simkaMerge`、`simkaMinCore`**
  全部 `target_link_libraries(... ${gatb-core-libraries})`
- `SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin)`
- 打包段：`INSTALL (DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin DESTINATION .)` 等

⇒ 一手结论：**simka 1.5.3 不是"库"，是命令行工具（application）**，无 `add_library`、无
`install(HEADER)`/`include` 导出、无 `cpp_info.libs` 可声明的对象。
按 R38/PF8：`package_type = "application"` 且**必须有软件级 `commands.json`**。
（台账"c/cpp 24 个"也对不上：simka 自身 src 只是小部分，大头在 vendored gatb-core。）

## 3. 依赖一手核（台账称"未在归档者=无"）

`.gitmodules` 实测：`submodule "thirdparty/gatb-core" → https://github.com/GATB/gatb-core.git`。
`api.github.com/repos/GATB/simka/contents/thirdparty?ref=v1.5.3` 给出 gitlink sha =
**`85335a59a98f99bdab2b67cf8d31d41d1897a61d`**。

⇒ **构建期必需的子模块就是这一枚 vendored gatb-core**（官方 tag 归档里是空目录 ⇒ 直接 configure 必炸）。⚠ 但「唯一」只覆盖子模块这一维：本包另有 1 个外部 conan 依赖 zlib/1.3.2（conanfile.py:39，见下条订正），⛔ 把本包当零依赖包。
gatb-core 该 commit **自身无 .gitmodules**（raw 取回 404），根树 = `.circleci .travis.yml README.md gatb-core`
⇒ 取 `https://github.com/GATB/gatb-core/archive/85335a59a98f99bdab2b67cf8d31d41d1897a61d.tar.gz`
解压进 `thirdparty/gatb-core/`（strip_root）即得上游期望的 `thirdparty/gatb-core/gatb-core/`。

`GatbCore.cmake`（同一 commit，raw 取回 HTTP=200）实测其搜索路径表：
`"gatb-core/gatb-core;../thirdparty/gatb-core;../../thirdparty/gatb-core/gatb-core;thirdparty/gatb-core;thirdparty/gatb-core/gatb-core"`
⇒ 上述布局命中最后一项，路径成立。

⚠ **口径订正（W4 r1 P2-3）**：本包**有**一个外部 conan 依赖 —— `conanfile.py:39` 的 `self.requires("zlib/1.3.2")`。**真因**（`conanfile.py:36-38` 自述）：gatb-core 的链接行写死 `-z` 且有 5 个源文件 `#include <zlib.h>`（解包树实测命中 `bank/impl/BankFasta.cpp`、`BankFasta.hpp`、`tools/collections/impl/B*` 等 5 枚）；⚠ **不是** HDF5 那条路——内嵌 HDF5 的 zlib filter 在本配方里显式关掉（`README.md:45`、`conanfile.py:76-77`、`manifest.yaml:17` 的 `-DHDF5_ENABLE_Z_LIB_SUPPORT=OFF` 三处同口）。交付期 requires 与安装读数见 `reports/w3-local-ci.log:168-169`、`:185`（`Requires` 行）与 `:172`（`Already installed`），第 32 行那是 **R36 注册表可读性**读数，不当作 requires 证据用。上面那条 preflight 读数写作"无依赖"是**时序错位**：预检跑在 `conanfile.py` 成形之前（配方还没落盘），所以 `[INFO] 未找到依赖声明` 只说明"当时无可读声明"，⛔ 拿它当"本包零依赖"的证据。zlib/1.3.2 的发布态由 W3 真跑时的 `Downloading`/`Already installed` 与 G2 `conan create 成功` 共同坐实。

## 4. 测试账本一手复算（台账"未见成体系 TESTS/add_test"）

- 主 `CMakeLists.txt`：**0 命中** `add_test` / `enable_testing` / `ctest` / `BUILD_TESTS`
  （且 `GATB_CORE_EXCLUDE_TESTS 1` 显式排除 gatb-core 测试）。
- **但上游根有 `tests/` 目录**（`api.github.com/repos/GATB/simka/contents?ref=v1.5.3` 实测列出）：
  `tests/` = `simple_test.py`、`simkaMin/`、`truth/`
  - `tests/simkaMin/` = `test_simkaMin.py`、`truth_simkaMin/`、`truth_simkaMin_symetrical/`
  - `tests/truth/` = `results_k21_t0`、`results_k21_t2`、`results_k31_t0`、`results_k31_t2`
- `tests/simple_test.py` 实读：显式 **5 个用例块** —— k=31/t=0、k=21/t=0、k=31/t=2、k=21/t=2
  （每个跑 `bin/simka -in example/simka_input.txt ... -kmer-size K -abundance-min T` 再 `test_dists()`
  与 `tests/truth/*` 逐行比对），外加 1 个 `test_parallelization()`（同输入两组
  `-nb-cores/-max-memory` 组合，比对两次产物一致）。它硬编码 `../build/bin/simka` 与
  `../example/simka_input.txt`，是"在 build 目录旁跑"的脚本，**不是 ctest 注册的测试**。

⇒ 申报口径：**无 ctest 注册测试（0 个 add_test），但有 5 个上游集成用例（Python 脚本 + truth 数据）**；
静态数如实写 5，运行/跳过/失败的拆分等实测后再填。⛔ 不得写"上游无测试"。

## 5. 设备工具链实测

`cmake version 4.1.2`、`ninja 1.13.1`、`Conan version 2.29.1`、
`clang version 15.0.4  Target: aarch64-unknown-linux-ohos`。
⇒ `cmake_minimum_required(VERSION 2.6)` 在 CMake 4 下是**必踩硬失败**（<3.5 兼容已移除）。

## 6. recipe-search / 知识图谱检索读数

`python3 scripts/ohc-run.py recipe-search simka` 原文：
```
⚠️ catalog.tsv 不存在，自动全量重建...
  ✅ catalog 重建: 6174 配方 → .../knowledge/recipes/catalog.tsv
  ⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板
```
⇒ 首稿无同族骨架可借，CMake 形态参考 `templates/conanfile-cmake.py.tmpl`。

## 7. 网络面实测（供披露，未做"修复"）

B 机到 `github.com:443` **间歇不通**（`curl: (28) Failed to connect to github.com port 443 after 25005 ms`，
多条；`api.github.com` 与 `raw.githubusercontent.com` 与 `deb.debian.org` 正常）。
官方 release 资产 `simka-v1.5.3-Source.tar.gz` 首轮下到 13,084,480/18,053,365 B 即 300s 超时。
⇒ 本方案**不依赖**该 18 MB 资产，改用 164 KB 官方 tag 归档 + gatb-core 官方 commit 归档（两个小件）。
本地绿不代表 CI 绿：CI 会把 GitHub 源改写进镜像且不校验状态码，下载件可能与 sha256 不符。

## 发现与知识（z74-simka3 收口轮 2026-09-27）

- ✅ 根因改判（一手探针 `~/tmp/uc2/z74-simka3/z74-simka3-probe.cpp` → `probe.out`）：卡点不是"list 末行缺 `\n`"本身，
  而是 gatb-core `CommonFile::gets()` 的跳字符循环用 plain `char` 承接 `fgetc()` 返回值——
  `FileSystemCommon.hpp:103` `for (char c = tmp[result-1]; c !='\n' && c!=EOF; c = fgetc (getHandle())) {}`；⚠ 补丁 hunk 头是 `@@ -93,21 +93,21 @@`（**93 是 hunk 起点、不是语句行**），从起点数第 11 行上下文才是 103 ⇒ 早期口径记成 `:93` 就是这么来的，以 103 为准；
  本机 `CHAR_MIN=0`（plain char 无符号）⇒ `c` 恒∈[0,255]、`c!=EOF` 永真；
  探针读数 `LOOP[char] iterations=100001（命中人为截断=无出口）`、`LOOP[int] iterations=1 且退出后 feof=1`。
- ✅ 由此**证伪交接处方 b)**（在 `BankAlbum.cpp:58` 循环里对 `gets` 返回长度 `<=0` 就 break）：死转发生在 `gets()` **内部**，
  函数从不返回，外层加 break 不可达；处方 a)（`SimkaAlgorithm.cpp:324/340` 仅在末字符是 `\n` 时才 erase）只绕开触发条件、
  不修根因，且 `Property.cpp:481` 的 `while (file->gets(...) != 0)` 同样暴露在同一缺陷上。
- ✅ 补丁落盘并登记：`patches/0001-thirdparty-gatb-core-gatb-core-src-gatb-system-impl-FileSystemCommon.hpp.patch`
  （`-` 行 = `for (char c = tmp[result-1];`，`+` 行 = `for (int c = static_cast<unsigned char>(tmp[result-1]);`），
  由 `refresh-patch --auto` 在**与目标树同构**的探索目录（`~/tmp/uc2/z74-simka3/explore/{orig,work}`）上生成，
  头两行 `--- a/thirdparty/... +++ b/thirdparty/...` 深度与 `source_folder` 一致；
  `conandata.yml` 的 `patches:` 段已登记（`patch_type: "bugfix"`）。
- ✅ 手工真跑（最终包 `~/tmp/ch/home-simka/p/b/simkaec6ef7d9e7e01/p`，`-kmer-size 21 -abundance-min 0
  -simple-dist -complex-dist`）：`rc=0`，产出 21 个 `*.csv.gz`；逐个 gunzip 后与上游
  `tests/truth/results_k21_t0/` 比对 **IDENTICAL=20 DIFF=0 MISSING=0**，
  `mat_presenceAbsence_jaccard.csv` 与 truth 的 sha256 同为
  `e23242a6857b2ecfb918150a3d63fa3d30d693c31605e9a2edb23b5a2d8387b7`。
- ✅ 产物形态事实：simka 1.5.3 的距离矩阵一律写成 `*.csv.gz`，**上游自己的** `tests/simple_test.py`
  先调 `decompress_simka_results()`（L16-24）解压成同名去 `.gz` 再 glob `*.csv` 比对（L31/L37）；
  21 个矩阵 = truth 的 20 个 + 由 Bray-Curtis 派生、上游注释明示不进 truth 的 `mat_abundance_jaccard`。
- ✅ 测试套超时护栏：`test_simka.sh` 里 3 处 simka 调用全部经唯一入口 `run_simka()`，
  已改为 `timeout -s KILL "${SIMKA_TIMEOUT:-180}"`，rc 124/137/143 一律判 **FAIL**（本机 toybox 0.8.12 实测
  `timeout 2 sleep 5`⇒124、`timeout -s KILL 2 sleep 5`⇒137）；断言分母 18 未动、未移出任何变体。
- ✅ 门禁读数（按 `grep -n -A1 "^## "` 的**子行**如实抄，⛔ 只抄表头）：`conan-verify-report.md` 第 3 行 `**Verdict**: PASS`；**G0 PASS 但第 11 行紧跟 `⚠️ 已知风险 E092 未在配方中处理`**（第 9 行 `**Knowledge hit**: E092`）、**G1/G2/G3 真 PASS**、**G4 只有第 43 行 `⚠️ 无法找到程序包 ID` 一行、未做任何 bin/lib/include 产物清点**、**L2/L4/L5 子行全是 `⏭️ 跳过（无 cache 路径）`**（一手代码依据：`scripts/ohc/conan_verify.py` L741 在 G4 处 early return，`self._cache_path` 到 L756 才赋值 ⇒ 三条走同一条 skip 分支）。⚠ 分栏说明：平台功能矩阵与产物基线的**确有执行读数**，但那是 **W3 内部步骤**（`ci/conan/build_and_test.sh` L1686-1691 是 **L2**（`timeout 15 "$bin_file" --version` → `[ok] L2: … --version OK`）、L1499-1501 是 **L5**（`[ok] L5: bin/ has content`），读数分别落在 `ci-metadata.json`:18 与 :20），**不是 conan-verify 的门禁** ⇒ ⛔ 把两者合并写成"各门 ✅ PASS"。
  `finish` 第 63 行 `✅ W3 本地 CI 模拟通过`；`.ci-result.json` =
  `exit_code=0` / `step=W3_local_ci` / `timestamp=2026-09-27T05:32:42.523471` / `integrity_hash=2c76006b3563ab7c`，
  其 `log_sha256` 与本机实算 `sha256sum reports/w3-local-ci.log` = `b4a654adbd94393fcaa16566b505252f74d47fc1cf380c0cf38e3577cb6644b6` 逐字符相同（互证）。
- ✅ 平台能力面（可复用于其它包）：同用户进程 **ptrace 被拒**（gdb `-p`/lldb `-p` 均 Permission denied）、
  **无 strace/ltrace** ⇒ 帧级栈在本机结构上不可得；可行替代是 `/proc/<pid>/{stat,wchan,syscall,io}` 采样
  + 读源码 + 写最小可编译探针直接复现语义（本轮据此把归因从"数据形态"下推到"实现定义的 char 符号性"）。
- ✅ B 素材检索（四路同扫 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/graph/index.tsv`）：
  本机制**已沉淀** = `knowledge/drafts/DRAFT-8543-plain-char-eof-sentinel-infinite-loop.{kv,md}`
  （looktxt/1.4.1 任务 #8543 同根因，rec_approach=widen-eof-receiver-to-int，与本补丁语义一致），
  相关条目 `knowledge/graph/E419.kv`（plain char 符号性的数值型症状，症状与处置不同）⇒ **B判定=hit，本 PR 不新建草稿/Issue**。
  ptrace 被拒/无 strace 这类可观测性缺口亦已有条目：`DRAFT-debugbreak-1.0-ohos-ptrace-gdb-test-equivalence`、
  `DRAFT-E5xx-ohos-musl-unwind-tables-empty-stacktrace`（grep ptrace 命中 21 件、strace 命中 20 件）。

## 收口台账（z74-simka3）

- 已做：补丁+登记、测试超时与两处错误前提修正、conan-verify PASS、finish/W3 通过、
  版本级 `manifest.yaml` 按实物建立、harness 杂件（`.patch-backup-*` 两个目录、
  `conandata.yml.ghfast-bak`、`conandata.yml.orig`）移出 worktree。
- 未做（留给主窗）：W4 独立审计、`reports/test-report.md`、`packaging/` 打包、
  `.staging-verified`、build-closed 标记（finish Step10 列出的 4 项未就绪），以及 PR 正文与 run。

**最终状态**：built —— `**Verdict**: PASS`、G0–G3 真 PASS（G0 带 E092 未处理告警）、G4 未做产物清点、L2/L4/L5 为 skip（详见「门禁读数」分栏）、W3 本地 CI 模拟通过、
`.ci-result.json` `exit_code=0`/`integrity_hash=2c76006b3563ab7c`、消费者测试 18/18 通过（`rc=0`）。
---

**编译结束**: 2026-09-27 05:40
**最终状态**: built

## 本地门禁补充登记
- ✅ **RREV 三档披露（W4 r1 P2-4，按实序如实登记，⛔ 宣称同一 rev）**：
  1. 本地 W3 绿跑当时 = `ed27eb712dfea7897592e6e7839cd8f4`（`reports/w3-local-ci.log:103` `[done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs` ⇒ 绿跑取的是 harness 预取的 `file://` 件，日志末尾有 `Pre-download: conandata.yml 已还原为官方 URL`）；
  2. 交付态第一次复算（本次整改前）= `3953eed3e7da5b0c90b2c470abad34c4`；
  3. 交付态当前 = `c09eab671c52581618c2e7557de1a874`（为把 `patch_description` 里「x86-64 有符号 char 平台行为不变」这句**过强且不实**的断言订正为『末字节恰 0xFF 时旧实现误判 EOF 提前退出、新实现继续跳行，属修正而非不变』而改动了 conandata 的一条描述串 ⇒ 修订号再翻一档）。
  ⇒ 四档之间的差异面**只有** conandata 的两条 `url:` 串与两条 `patch_description` 描述串（第 4 档是为把「唯一行为差是末字节 0xFF」这句过强量化改成「任意被跳过的字节恰为 0xFF」而重算的）：两处 `sha256`、`destination`、`patches` 的 `patch_file`/`patch_type`、`conanfile.py` 与补丁本体逐字节未动 ⇒ 编译与测试证据指向同一份代码。
  - ⚠ **不写成「CI 会首次真执行官方址」**（W4 r2 P3-2 反证）：CI 跑的是同一份 `ci/conan/build_and_test.sh`，其 L1164-1189 就是 Pre-download 段（curl 取 conandata 里的 URL → 改写成 CI 机器本地的 `file://` → trap 还原，L1185 打印「Pre-download: conandata.yml 已还原为官方 URL」；L1155-1162 另有 mirror fallback，:547 脚本自述同义）⇒ **conan 原生 HTTPS 取源在本地与 CI 两侧都没有真跑**，属 harness 取源形态而非本包缺陷；真取源由 pre-download 的 curl 完成，其成败按 `[step] Pre-download` / `[cached]` / `[WARN] … will rely on conan's download` 四类行判定，⛔ 预先断言。
