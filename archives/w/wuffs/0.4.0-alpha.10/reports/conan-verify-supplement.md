# conan-verify 补充报告 — wuffs 0.4.0-alpha.10

> 生成时间：2026-09-10
> 对应 SHA：见 PR 正文（采信轮 `reports/conan-create-log.md` 的轮次）

## 1. 为什么需要本报告

`reports/conan-verify-report.md` 的工具判定是 `G4: ✅ PASS` / `L2: ✅ PASS` /
`L4: ✅ PASS` / `L5: ✅ PASS`，但同一文件里这四项的实际行是：

```
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID
## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

`wuffs` 是 `package_type = "header-library"` 且 `package_id()` 调用了
`self.info.clear()`（package_id 恒为 `da39a3ee5e6b4b0d3255bfef95601890afd80709`），
命中已知缺陷：工具的 package_id 解析在这个形态下失败 → G4/L2/L4/L5 全部
**静默跳过却仍判 PASS**（`✅ PASS` 与 `⏭️ 跳过` 并存的工具文案缺陷）。

按第 7.2 节口径，跳过项必须以显式 SKIPPED 对待并人工补测。下面四项均为
本节实测，不是工具输出。

实际包目录一律用 glob 定位（工具默认路径在 header-only 形态下解析失败）：

```
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/wuffs*/p | head -1)
```

> **不要在本报告里找固定的分片目录名**：`p/<首字母>/<名前5字符><hash>` 这个 hash
> 每次清缓存重建都会变（本项目实测已出现 `wuffs3d82577138280`、`wuffs3be1f9f0633cf`、
> `wuffs4f00ef893a778`
> 等多个），任何写死的目录名在下一轮即不存在、无法现场复核。本节的所有判据都只依赖
> 与目录名无关的量：文件清单、退出码、ELF 属性与 sha256（`artifacts_baseline` 段给出
> 交付产物 `wuffs-v0.4.c` 的 sha256，审计方已用 `tar -xzO` 从上游 tarball 独立复算命中
> `1f8039ef82911604c063f6ac2ed57254bdb17d742aebdeae06356530d4a0fde7`）。

---

## 2. G4 产物完整性（人工实测）

`package()` 声明安装 1 个单文件产物 + 3 个许可证；实际落盘：

```
$ find <pkg>/p -type f | sort
conaninfo.txt
conanmanifest.txt
include/wuffs/wuffs-v0.4.c
licenses/LICENSE
licenses/LICENSE-APACHE
licenses/LICENSE-MIT
```

| 声明（package/manifest） | 实际存在 | 结论 |
| --- | --- | --- |
| `include/wuffs/wuffs-v0.4.c` | ✅ | 一致 |
| `licenses/LICENSE` | ✅ | 一致 |
| `licenses/LICENSE-APACHE` | ✅ | 一致 |
| `licenses/LICENSE-MIT` | ✅ | 一致 |

`conaninfo.txt` 为空文件、`conanmanifest.txt` 为 Conan 元数据，属工具生成物，
非包内容。

**结论：G4 PASS（人工核实，工具跳过）。** 无声明缺失，无未声明多余产物。

---

## 3. L2 消费者实测（人工实测）

R34/L1e 要求的破坏性反向验证与真实消费者运行，在一个**只使用包内
`include/` 目录**（不接触仓库源码树）的独立目录中完成：

```sh
mkdir -p suppl-consumer/include
cp -a <pkg>/p/include/wuffs suppl-consumer/include/

CC=/data/service/hnp/bin/clang ; CXX=/data/service/hnp/bin/clang++
$CC  -std=c99   -Wall -Wextra -Werror -I include -I <test_package> -c test_package/test_wuffs.c -o tw.o
$CC  -std=c99   -Wall -Wextra -Werror -I include -I <test_package> -c test_package/test_wuffs_header_only_tu.c -o tw_hdr.o
$CXX -std=c++17 -Wall -Wextra -Werror -I include -I <test_package> -c test_package/test_wuffs_cpp.cpp -o tw_cpp.o
$CXX tw.o tw_hdr.o tw_cpp.o -o test_wuffs
./test_wuffs
```

真实输出：

```
OK: 15 checks passed, 0 failed
```

（退出码 0。该程序校验 `WUFFS_VERSION == 0x000040000` 与
`WUFFS_VERSION_STRING` 前缀，解码内嵌 4×4 PNG 到 24bpp RGB 并与独立计算的
`crc32=0x6B64E606` / `adler32=0x3A8710A1` 比对，见 `test_package/test_wuffs.c`。）

**破坏性反向验证**：把被测产物改名后同名编译必须失败——

```sh
mv include/wuffs/wuffs-v0.4.c include/wuffs/wuffs-v0.4.c.bak
$CC -std=c99 -I include -I <test_package> -c test_package/test_wuffs.c -o /dev/null
```

```
编译退出码=1
In file included from .../test_wuffs.c:34:
.../wuffs_test_config.h:38:10: fatal error: 'wuffs/wuffs-v0.4.c' file not found
    #include <wuffs/wuffs-v0.4.c>
```

即测试**真实依赖被测包**，不是空壳（随后已还原文件）。

**结论：L2 PASS（人工补测，工具跳过）。**

---

## 4. L4 安全属性（人工实测）

wuffs 交付的是一个 `.c` 源文件，**包内不存在任何 ELF 产物**，因此
NX/PIE/RELRO 扫描对本包没有适用对象。实测：

```
$ find <pkg>/p -type f | while read f; do ... # 检查 ELF magic 7f 45 4c 46
包内 ELF 文件数 = 0

$ find <pkg>/p -type f -exec file {} \;
include/wuffs/wuffs-v0.4.c: ASCII text
licenses/LICENSE:           ASCII text
licenses/LICENSE-APACHE:    ASCII text
licenses/LICENSE-MIT:       ASCII text
conaninfo.txt:              empty
conanmanifest.txt:          ASCII text
```

工具报告的“跳过（无 cache 路径）”在本包属于**正确的不可用**，而非漏测：
包本身没有可扫描的 ELF。

作为平台 ELF 能力佐证（**不是**交付产物），本次消费者程序由同一 OHOS clang
15.0.4 产出，安全属性齐备：

```
readelf -lW test_wuffs | grep -E 'GNU_STACK|GNU_RELRO'
  GNU_RELRO  0x04fed0 ... R  0x1
  GNU_STACK  0x000000 ... RW 0        # 无 E 位 → NX 生效
readelf -dW test_wuffs | grep -E 'BIND_NOW|FLAGS'
  (FLAGS)    BIND_NOW
  (FLAGS_1)  Flags: NOW PIE          # 完整 RELRO + PIE
```

**结论：L4 对本包不适用（包内零 ELF，已实测）；以“不适用”记录，不写成 PASS。**
平台侧的安全属性佐证如上。

---

## 5. L5 产物基线（人工实测）

交付产物 sha256 与上游 tarball 内原始文件逐字节比对：

```
$ sha256sum <pkg>/p/include/wuffs/wuffs-v0.4.c
1f8039ef82911604c063f6ac2ed57254bdb17d742aebdeae06356530d4a0fde7

$ sha256sum <src>/release/c/wuffs-v0.4.c
1f8039ef82911604c063f6ac2ed57254bdb17d742aebdeae06356530d4a0fde7

$ cmp <pkg>/p/include/wuffs/wuffs-v0.4.c <src>/release/c/wuffs-v0.4.c
cmp: IDENTICAL
```

许可证同样逐字节一致：

| 文件 | 包内 sha256 | 源码树 sha256 | 结论 |
| --- | --- | --- | --- |
| `LICENSE` | `f8ac2c75…d19cb` | `f8ac2c75…d19cb` | IDENTICAL |
| `LICENSE-APACHE` | `0d542e0c…e94594` | `0d542e0c…e94594` | IDENTICAL |
| `LICENSE-MIT` | `bb811a4b…0bc878` | `bb811a4b…0bc878` | IDENTICAL |

基线值已写入版本级 `manifest.yaml` 的 `verification.artifacts_baseline`。

**结论：L5 PASS（人工补测，工具跳过）。** 无漂移：安装的是上游 tarball 的
原始字节，未经任何后处理改写（本包 `package()` 只 copy，不编译产物，也不存在
meson `--destdir` 改写 `.dynstr` 那类风险）。

---

## 6. 采信轮记录

> 本节结论对应**最终 SHA**：本文档提交时的 `conan create` 输入
> （`conanfile.py` + `conandata.yml` + `patches/` + `test_package/`）与采信轮
> 完全一致——W4 独立审计已用 `git diff` 复核该四路径在采信轮之后无改动，
> 仅 `reports/` 与 `knowledge/drafts/` 有文档类提交（不进 `conan create` 输入）。
> 采信轮日志本体已**逐字**转存为 `reports/conan-create-log.md` 并随 PR 提交，因此证据
> 指针在 PR diff 内可追溯；原始 `reports/conan-create.log` 属构建运行日志，按
> `.gitcode/review-memory.md` 规则 19（`*.log` 一律不入库）不再随 PR 提交，只留在
> 任务私有目录。工具报告 `reports/conan-verify-report.md` 的 `📄 日志:` 行仍写原始
> `.log` 名（生成器硬编码该文件名，该文件保持工具原样输出未手改），与本文档的
> 映射关系即本段。

- 清缓存：`rm -rf ~/.conan2/p/*/wuffs* ~/.conan2/p/wuffs*` +
  `conan remove "wuffs/*@*" -c`（枚举 user/channel 形态），随后
  `p/cache.sqlite3` 的 `recipes`/`packages` 两表按 `%wuffs%` 查询均为空
  （`DB_CLEAN`），无幽灵条目。该清缓存 + 重跑共做了**三轮**：第一轮对首轮 SHA `fad1f35b`；第二轮在 W4 首轮
  fail 的修复后（`sources.url` 形态 + 文档订正）；第三轮在第二轮审计的 P2/P3
  修复后（`package_info` 显式声明空 `cpp_info.libs`，属 `conan create` 输入变更，
  按第 7.5 节必须重验）。本节记录的是**第三轮**。
- G2 干净轮在全新构建目录完成（目录名逐轮重建，**以入库日志记录的为准**而不是
  以本文档某轮抄下的名字为准）：
  `~/.conan2/p/b/wuffs4f00ef893a778/b/build-release`——该字符串取自
  `reports/conan-create-log.md` 自身的 `Building your package in …` /
  `Build folder …` / `Package folder …` 三行，可直接在 PR 内 grep 复核
  （`grep -n 'Build folder\|Package folder' reports/conan-create-log.md`）；
  日志含 4 条 `coherence check OK`、30 条
  `RUN: clang -std=c99 -Wall -Werror "test/c/std/*.c"`（逐程序编译）
  与 30 条测试运行。可直接核验的关键行：
  ```
  upstream C tests: 30 programs, 232 test cases, all PASS
  golden regression OK: test/nia-checksums-of-data.txt (202 entries)
  golden regression OK: test/mzcat-checksums-of-data.txt (34 entries)
  OK: 15 checks passed, 0 failed
  ```
  日志第 66 行的源下载行还印证了 `sources.url` 换形态后的镜像兜底确实生效：
  ```
  Sources correctly downloaded from
    https://ghfast.top/https://github.com/google/wuffs/archive/refs/tags/v0.4.0-alpha.10.tar.gz
  ```
  （该消息由 Conan 在 sha256 校验通过之后打印。）
- **关于日志覆盖风险（第一轮实测，作为工具缺陷证据保留）**：首轮采信轮日志
  （31696 B）在 `finish` 内嵌重跑时曾被 7928 B 的缓存命中轮覆盖——该轮
  `grep -c 'RUN: .*clang -std=c99'` = 0、也没有汇总行，可据此识别；当时靠运行前
  留存的副本回填。此后各轮已不再依赖该补救：`conan-verify` 跑完立即把当轮日志复制
  到任务私有目录（仓库外），并**逐字**转存为 `reports/conan-create-log.md` 入库
  （原始字节数 32736 / 行数 356 / sha256
  `2706666a65d9b0f4a258f4a88e21abe4437e10b0034086e46afee671a569f49d` 写在该文件头部）。
  **抽取命令已在该文件内写死**（取 ```` ```text ```` 之后、最后一个 ```` ``` ```` 之前的
  全部字节，不再剥末尾换行），避免围栏边界口径歧义；这些轮之后未再跑 `finish`
  （其内嵌重跑是覆盖源）。
  **留档随配方改动而重生成**：`conanfile.py` 的内容计入 recipe revision，故配方一经改动
  （哪怕只是注释）该轮日志就不再对应新 HEAD，必须用新一轮重新生成留档——本 PR 的 rule19
  轮与第九轮审计修复轮正是这样各换过一次（见第 11、12 节）。
  **rrev 判据（第十轮审计 P3-DOC-RREV 更正）**：留档头部记录的 rrev 是 **create 执行期**
  的物料指纹——`scripts/ohc/conan_verify.py` 会在 create 前把工作区 `conandata.yml` 的
  `https://github.com` 就地替换为 `https://ghfast.top/https://github.com`（create 后回滚），
  因此该 rrev 对应**镜像态** conandata.yml，而对 HEAD 的官方态物料单独 export 会得到**另一个**
  rrev。该差异是工具行为、不是包内不一致；本报告只用它做**跨轮可比性**判据。
- 工具提示 “✅ 可标记 status: published” 按第 1.2 节忽略：release upload
  未确认，状态记 `built`。

---

## 7. `finish` 收尾结果判读

`finish wuffs 0.4.0-alpha.10 built` 退出码 1，失败步骤全部落在第 7.2 节实测
白名单内，且阻塞门禁均为 PASS：

| 步骤 | 结果 | 判读 |
| --- | --- | --- |
| Step 4 内嵌 `conan-verify` | ✅ `配方验证通过` | 阻塞门禁 PASS |
| Step 5 内嵌 W3（`build_and_test.sh`） | ✅ `L0_RESULT=pass` / `L1_RESULT=pass` / `L1e` 破坏性反向验证通过 | 阻塞门禁 PASS；该次运行对应旧配方，**第三轮已按第 7.5 节对最终配方重跑 W3**（第三轮 W3 结果见本文档第 9 节内联的关键行：`L0_RESULT=pass` / `L1_RESULT=pass` / `L1e` 通过 / 232 programs PASS / `OK: 15 checks passed`；该轮日志本体按规则 19 未入库） |
| Step 2 `close-archive` | ✅ `档案已关闭: built` | 归档 closed→built |
| Step 3 内嵌 G0 预检 | ❌ `configure 失败 (exit 127)` | 白名单：该预检硬编码 `./configure`，wuffs 上游无 configure（BUILD.md 明确无构建步骤） |
| Step 7 W5 知识图谱 | ❌ `E219/E253/E305.kv: root_cause 为空` | 白名单：仓库级存量缺口，本包 `graph validate 通过` |
| Step 10 submit 就绪预检（step5b） | ❌ `test-report.md` / `packaging/` / `.staging-verified` | 白名单：ARCHIVE-SPEC v3.0 已废弃 `packaging/`，submit 流程不使用 |
| Step 8 SUMMARY.md 重建（step8） | ⚠️ `收录软件 2515 款 → 1 款` | 白名单数据破坏级副作用，已 `git checkout --` 还原，未提交 |
| Step 6 `finalize-archive` | ⚠️ RC=2 | 白名单（`packaging`/tar.gz 缺失）+ 见下条工具缺陷 |

`finalize-archive` 另报 **`补丁数不一致: manifest=30 vs disk=9`**，并打印
`补丁: 9 个`。这是**工具计数缺陷，不是包问题**：`scripts/ohc/finalize_archive.py`
用 `(ver_dir / "patches").glob("000*.patch")` 计数，`000*` 只能匹配
`0001`–`0009` 九个文件名，`0010`–`0030` 因前缀变成 `001`/`002`/`003` 而漏计。
磁盘实际为 30 个补丁（`ls patches/ | wc -l` = 30），与 `conandata.yml` 声明、
`manifest.yaml` 的 `patches_applied` 完全一致。详见
`feedback/pending/2026-09-10-wuffs-0.4.0-alpha.10.md`。

`finish` 的其余已知副作用同样逐个审查并还原（全部 `git status` 干净收尾）：
`manifest.yaml` 的 `patch_generation`/`patch_classification` 被改写为
`auto/pending`、`notes.md` footer 追加、`reports/conan-verify-report.md` 仅
`Date` 变化、`SUMMARY.md` 重建、`.build-cache/` 垃圾。四项均已 `git checkout --`
还原为提交版；`reports/conan-verify-report.md` 回到提交版不构成新 SHA。

---

## 8. W4 独立审计的修复闭环

第一轮 W4 独立审计（`verdict=fail`，P0=1/P1=0）判定：`notes.md`、
`reports/native-build-test.md`、`knowledge/drafts/E565-draft-CBFA.md` 三处把
`g_tests[]` 的静态计数写成「共 242 个元素，其中 10 个在 `#ifdef WUFFS_MIMIC` 内」。
审计者独立复算为 **295 / 63**（默认口径 232）。

**该 P0 成立，本轮已修复。** 复核过程与结论：

- 错因（自我定位）：早期统计用的正则以非贪婪方式删除 `#ifdef ... #endif` 块，
  误删了大量非 mimic 区域，得到偏小的假总数；改用 `clang -E` 真实预处理后，
  又因未滤除 `# <line> "<file>"` linemarker 而每个文件多计 1 个伪元素
  （得到 242 / 295 的假口径）。两者叠加后「总数」与「默认口径」同时出错，
  且错得互相自洽（232 + 10 = 242）。
- 正确取数（括号配平解析 `g_tests[]` + 滤除 linemarker + 去掉末尾 NULL 哨兵）：
  `-DWUFFS_MIMIC` 定义时总数 **295**，宏内 **63**，未定义该宏的默认口径 **232**；
  逐文件与实跑产生的 30 条 `PASS (N tests)` **30/30 完全吻合**（吻合关系是本轮
  订正的独立校验）。**证据文件须写准**：`conan create` 日志里没有逐程序 PASS 行
  （配方把每个程序的 stdout 重定向到 `<name>.out` 再断言），只有汇总行
  `upstream C tests: 30 programs, 232 test cases, all PASS`；那 30 条逐程序 PASS 行
  的原始输出见 `reports/upstream-c-tests-log.md`（31 行，末行
  `FILES=30 TEST_PROCS=232 FAILED_FILES=0`，逐字留档）。
- 订正落点：`notes.md`（3.3 节 + 3.4 节表格）、`reports/native-build-test.md`
  （3 节 + 7 节表格）、`test_package/MANIFEST.yml`（`not_run` 段）、
  `manifest.yaml`（`tests.upstream_not_run`）、
  `knowledge/drafts/E565-draft-CBFA.md`（草稿的 `.kv` 从未包含这两个数字）。
  各处均保留「勘误」说明而不是静默替换，并把取数命令与两个陷阱写入文档，
  避免同类错误再次发生。第二轮审计进一步修正了陷阱描述的精确度：整文件带
  `-DWUFFS_MIMIC` 预处理会因缺第三方头文件在 10/30 个文件上失败（须先取出
  `g_tests[]` 块再预处理）；而 linemarker 导致的 +1 只发生在实际触发该合并的
  10 个文件上（`g_tests[]` 内含 mimic 分支的文件共 28 个，其中 10 个命中；
  232 → 242），不是「每个文件 +1」。
- 其余审计发现同轮处置：P2 两处文件大小（`wuffs-v0.4.c` = 3 625 906 B；
  snapshot = 3 625 807 B）与仓库 URL 形态存量统计已订正；P3 中的
  「方法内 `import subprocess`」已上移到模块顶部、
  「`strip=1` 口径不精确」已改为 Conan 实走的 `strip=0`、
  「被 gitignore 的日志被当证据引用」已通过**逐字 `.md` 留档**
  （`reports/conan-create-log.md`）解决、
  「codeload URL 不触发 CI 镜像兜底」已把 `sources.url` 换成
  `github.com/.../archive/refs/tags/<tag>.tar.gz` 形态（sha256 不变，实测与
  codeload 形态字节一致）。
- 本轮计量结论未变：上游 **232/232**、消费者 **15/15**，两者都不依赖上述分解项。

审计报告（第一轮 fail）留档于任务私有目录 `audit-result-round1-fail.json`；
最终 SHA 的审计结论以 `reports/audit-result.json` 为准，并在 PR 正文转述。

---

## 9. 最终 SHA 上的 W3 重跑（第 7.5 节要求）

第三轮修复触及 `conanfile.py`（`package_info` 显式声明空 `cpp_info.libs`）——它是
`conan create` 的输入，因此按第 7.5 节「修改 → 重跑全部受影响的验证」必须重跑 W3，
而不能沿用 `finish` 在旧配方上跑出的那一轮 W3 结果。

重跑方式与 `finish` 内部完全一致（`scripts/ohc/workflow_checks.py:186-206`）：

```sh
zsh ci/conan/setup.sh
CI_PACKAGES=archives/w/wuffs/0.4.0-alpha.10 \
CI_REPO_ROOT="$PWD" \
  zsh ci/conan/build_and_test.sh archives/w/wuffs/0.4.0-alpha.10
```

**关于运行日志的入库口径**（规则 19：`*.log` 一律不入库）：

- `.gitcode/review-memory.md` 规则 19「PR 中禁止的文件」字面列举了 `*.log`，
  **规则文本没有豁免条款**。仓库现状与该条文并不一致——`git ls-tree -r
  upstream/main` 实测仍有 **35 个跟踪的 `*.log`**，其中 **32 个在 `reports/` 下**、
  **17 个包**跟踪 `reports/conan-create.log`（该路径同时被 `.gitignore` 覆盖，即均为
  `git add -f` 入库）——但既有存量不构成本 PR 新增的理由，故本 PR 提交面
  **不含任何 `*.log`**。
- `conan create` 采信轮日志（32736 B / 356 行 / sha256
  `2706666a65d9b0f4a258f4a88e21abe4437e10b0034086e46afee671a569f49d`）
  **逐字**转存为 `reports/conan-create-log.md`：正文是 fenced 代码块，与原文件
  逐字节相同（抽取代码块后 `sha256sum` 可复核），头部声明上述元数据与生成命令。
  原始 `.log` 只留在任务私有目录（仓库外），不随 PR 提交。
- 本轮 W3 日志（467 行，sha256
  `bafefce6406b4d10ed434f12a5516b30b870a8851d0552b7a9a87d08ea1afd8b`）同样
  **不随 PR 提交**，只在本文档内联全部关键结果行（见下）与可复现命令。
- `reports/conan-verify-report.md` 是工具原样输出，其 `📄 日志:` 行仍写原始 `.log`
  名（`conan_verify.py` 硬编码该文件名），本文档与 `manifest.yaml`、`notes.md`、
  `native-build-test.md`、`test_package/MANIFEST.yml` 的引用均已指向 `.md` 留档。

结果：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=warn: no artifacts found
━━━ Build Summary ━━━
  Total:   1   Success: 1   Failed: 0   Pass rate: 100.0% (1/1)
```

其中与本包直接相关的证据行：

```
[ok] L0m: directory structure valid
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1e: Negative test confirmed — test genuinely depends on wuffs
wuffs/0.4.0-alpha.10: upstream C tests: 30 programs, 232 test cases, all PASS
wuffs/0.4.0-alpha.10: golden regression OK: test/nia-checksums-of-data.txt (202 entries)
wuffs/0.4.0-alpha.10: golden regression OK: test/mzcat-checksums-of-data.txt (34 entries)
RUN: ./test_wuffs                  → OK: 15 checks passed, 0 failed
RUN: ./ohos_platform_test          → OK: 32 checks passed, 0 failed   (NEON 路径)
RUN: ./ohos_platform_test_portable → OK: 32 checks passed, 0 failed   (可移植路径)
# 本构建 have_arm_crc32() = 0（OHOS clang 15 默认目标未定义 __ARM_FEATURE_CRC32）
```

`L2_RESULT=skip`（包内无 `bin/`，非 CLI 工具）与 `L5_RESULT=warn`（包内无
`bin/`/`lib/` 二进制）属形态固有，不是失败；对应的安全属性与产物基线已在
本文档第 4、5 节人工补测。

**副产物：`sources.url` 换形态的效果在真实 CI 脚本里得到直接验证。** 本轮 W3 的
预下载阶段输出（原日志第 93-99 行）：

```
[step] Mirror fallback: rewriting source URLs in conandata.yml...
        [ok] Source URLs rewritten with mirror fallback
[step] Pre-download: extracting source URLs from conandata.yml...
  found 2 source URL(s)
  [try 1/1.1/3] v0.4.0-alpha.10.tar.gz ← https://gh-proxy.com/https://github.com/google/wuffs/archive/refs/tags/v0.4.0-al...
  [ok] v0.4.0-alpha.10.tar.gz (15384KB) via mirror 1
...
[done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
```

即 `github.com/.../archive/refs/tags/<tag>.tar.gz` 形态确实命中
`ci/conan/build_and_test.sh` 的镜像改写正则（旧 codeload 形态不命中），W4 第二轮
P3-3 的修复在真实脚本路径上得到确认。

**同轮再次复现已知工具缺陷**：该脚本尾部打印
`[step] Pre-download: conandata.yml 已还原为官方 URL`，但运行后
`git diff conandata.yml` 显示文件实际仍是镜像列表形态：

```diff
-  url: "https://github.com/google/wuffs/archive/refs/tags/v0.4.0-alpha.10.tar.gz"
+  url:
+    - "https://gh-proxy.com/https://github.com/google/wuffs/archive/refs/tags/v0.4.0-alpha.10.tar.gz"
+    - "https://github.com/google/wuffs/archive/refs/tags/v0.4.0-alpha.10.tar.gz"
```

与第 7.2 节登记的「`finish` 的『已恢复原始』日志不可信」同族，本轮已
`git checkout --` 还原，未提交。该次运行同时留下 `.build-cache/` 与 `.ci_logs/`
垃圾，已删除。

---

## 10. rule12（鸿蒙特有测试）修复记录

外部评审（pc-pr-review）在 SHA `9aad15ad` 上给出 `VERDICT=FAIL`，唯一失败项是
**rule12 鸿蒙特有测试 N=0 < 1**。评审同时核实上游 N 实测 227 ≤ 声明 232，其余
11 条规则全部 PASS。

初版把该栏填 0 的理由是「wuffs 是纯 C99 单文件库，未引入平台特有 API/行为」。
该判断在**测试覆盖层面**是错的：wuffs 在**编译期**按 CPU 架构选择代码路径，
`release/c/wuffs-v0.4.c` 的配置段写明 ARM 快速路径的前提是
**小端序 + 可用的非对齐访存**——这正是平台属性，而且它决定了「跑的到底是哪份
代码」。纯可移植 C 测试永远发现不了这类问题，因为可移植路径不是实际执行的那条。

新增 `test_package/ohos_platform_test.c`（同一源文件两次构建）：

| 可执行文件 | 关键标志 | 库自报选中路径 | 断言数 |
| --- | --- | --- | --- |
| `ohos_platform_test` | 默认 | `have_arm_neon() == 1` | 32 |
| `ohos_platform_test_portable` | `-DWUFFS_CONFIG__AVOID_CPU_ARCH` | `have_arm_neon() == 0` | 32 |

覆盖内容：平台前提（小端序、LP64、经 `memcpy` 实测的非对齐 64 位小端读写往返）；
未误选 x86 SSE4.2/AVX2；**从 16 个非对齐输入偏移**各解码一次内嵌 PNG 并要求
`crc32(解码 RGB) == 0x6B64E606`（Python `binascii.crc32` 独立算出）；所选 CRC-32
实现与标准校验值 `0xCBF43926` 一致（实测本构建 `__ARM_FEATURE_CRC32` 未定义、
`have_arm_crc32() == 0`，故走**可移植实现**；该断言校验取值契约而非机制）。

源文件在**两个方向**上都断言所选路径，故两次构建可证明真的走了不同实现
（二进制大小 379328 vs 362944 B、哈希不同），两者又必须满足同一组已知答案——
因此「一致」是真实的 NEON-vs-可移植等价性结论，而非同义反复。

本轮已按第 7.5 节清缓存重跑 `conan create` 与 W3（`test_package/` 与
`CMakeLists.txt` 属 `conan create` 输入，必须重验）。设备实测：

```
RUN: ./test_wuffs                    →  OK: 15 checks passed, 0 failed
RUN: ./ohos_platform_test            →  OK: 32 checks passed, 0 failed
RUN: ./ohos_platform_test_portable   →  OK: 32 checks passed, 0 failed
# build: default (aarch64 fast paths enabled)
# wuffs_base__cpu_arch__have_arm_neon()     = 1 (want 1)
# build: portable (WUFFS_CONFIG__AVOID_CPU_ARCH): arch-specific code disabled
# wuffs_base__cpu_arch__have_arm_neon()     = 0 (want 0)
upstream C tests: 30 programs, 232 test cases, all PASS
L0_RESULT=pass / L1_RESULT=pass / L1e 反向验证通过
```

计数：上游 232（不变）；`test_package` 合计 **79**（15 消费者 + 32 + 32），
其中**鸿蒙/aarch64 平台专项 64**。上游用例口径不受影响，两者分栏统计。

---

## 11. rule19 改造轮的清缓存重验

本轮修复把入库的 `reports/conan-create.log` 逐字转存为 `reports/conan-create-log.md`
（规则 19 禁止 `*.log` 入库），并同步改写了 `test_package/MANIFEST.yml` 中的注释引用。
该文件位于 `test_package/` 下，按改动分级判据落在构建输入路径内，因此本轮**不沿用**
上一轮证据，重新做了清缓存重验：

- 清缓存四步（限 ref + 裸 ref + 分片目录 + `p/cache.sqlite3` 两表按 `wuffs/%` 回查）
  输出 `recipes: []` / `packages: []` / `DB_CLEAN`，无幽灵条目。
- 命令与第 6 节同一条：`python3 scripts/ohc-run.py conan-verify wuffs 0.4.0-alpha.10
  --project-dir <repo>`，rc=0、`✅ 配方验证通过`。
- 干净轮标志（当轮原始日志的仓库外副本 `conan-create-rule19.log`）：
  `Apply patch` 30 条、`RUN: /data/service/hnp/bin/clang -std=c99` 34 条、
  ```
  upstream C tests: 30 programs, 232 test cases, all PASS
  golden regression OK: test/nia-checksums-of-data.txt (202 entries)
  golden regression OK: test/mzcat-checksums-of-data.txt (34 entries)
  OK: 15 checks passed, 0 failed      （test_wuffs）
  OK: 32 checks passed, 0 failed      （ohos_platform_test）
  OK: 32 checks passed, 0 failed      （ohos_platform_test_portable）
  ```
- recipe revision：`wuffs/0.4.0-alpha.10@ohpcd/stable#fcd12342d7b9cb9a35ffbde78a7a75d8`
  ——与上一采信轮**同一 rrev**。即本轮改动未触及导出物料（`conanfile.py`/`conandata.yml`/
  `patches/` 逐字节未变），第 6 节的采信轮证据在本轮 SHA 上继续有效；本轮是同 rrev 的
  再次独立复现（清缓存后的全新构建目录）。
  **rrev 沿革（重要）**：紧接着的第九轮审计修复改动了 `conanfile.py`（P2-1 注释纠正），
  导出物料随之前移，rrev 变为 `123c2bd7b1deae5b1b5d70fb2261d1ca`；因此入库的逐字留档
  `reports/conan-create-log.md` 已用那一轮的日志重新生成（见第 12 节），其头部 rrev 与
  当前 HEAD 一致。
- W3（`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`，与 `finish` 内部同路径）：
  `L0_RESULT=pass` / `L1_RESULT=pass: test_package executed` / `L2_RESULT=skip: no bin/ dir` /
  `L4_RESULT=pass: patches clean` / `L5_RESULT=warn: no artifacts found`、
  `Pass rate: 100.0% (1/1)`；日志仓库外副本 `w3-local-ci-rule19.log`（按规则 19 不入库）。
- 本轮工具副作用（实测留证、已还原）：`conan-verify` 把 `conandata.yml` 的 `sources.url`
  就地改写成两元素列表（`https://gh-proxy.com/<官方 URL>` + 官方 URL，`sha256` 不变），
  并新建 `.build-cache/predl_cache/` 下两个缓存 tarball（`.gitignore` 未覆盖该目录）。
  两者已分别用 `git checkout -- conandata.yml` 与 `rm -rf .build-cache` 还原，
  收尾 `git status --short` 为空、`git diff HEAD` 为空。
- 判据说明：本轮与上一轮的日志**不可能逐字节一致**（内嵌 `Exported: … (… UTC)` 时间戳与
  每轮重建的缓存分片目录名不同），故采信判据是「构建输入 diff 为空 + 干净轮标志」，
  不是日志字节可复现（第 6 节同此口径）。

---

## 12. W4 第九轮审计（P2×2 / P3×8）修复记录

第九轮独立审计对被审 SHA `d944ba4c76` 给出 `verdict=pass`（**P0=0、P1=0**），
遗留 2×P2 + 8×P3。逐项处置如下（每条给判据与落点）。

**P2-1 注释过度声明（`conanfile.py`）**：原注释称 build-all.sh 的 example 端到端检查
「通过 include 补丁取到版本化产物，因此覆盖了被交付文件」。**该说法错误**：30 个
portability 补丁只改 `test/c/std/*.c`，而 `example/{crc32,mzcat,jsonptr,convert-to-nia}`
4/4 仍 `#include "../../release/c/wuffs-unsupported-snapshot.c"`（与上游 `build-all.sh`
一致）。已把注释改为写明 **SCOPE**：该段是配方编译/运行管线的**上游一致性**检查，
不构成关于交付文件的证据；交付产物由 30 个已重定向的 `test/c/std` 程序与
`test_package/` 覆盖。复核命令：
`grep -rn '#include.*release/c/wuffs' example/{crc32,mzcat,jsonptr,convert-to-nia}/*`
→ 4/4 为 snapshot。**该修复触及 `conanfile.py`（`conan create` 输入），故本轮再次
清缓存重跑 `conan create` 与本地 CI 模拟。**

**P2-2 证据指针与实物不符**：三处（`notes.md`、`test_package/MANIFEST.yml`、
本文档第 8 节）称 232 的静态计数「与实跑日志的 30 条 `PASS (N tests)` 逐文件吻合」，
但 `conan create` 日志里**没有**逐程序 PASS 行——配方把每个程序的 stdout 重定向到
`<name>.out` 后只断言「含 PASS 行且 N>0」，日志正文只剩汇总行
（`grep -c 'PASS (' <对 reports/conan-create-log.md 的正文代码块> ` → **0**；该计数必须
限定在代码块内——该文件头部说明文字里会出现被检索的模式本身，对整份文件计数会自我命中，
本项目相邻两轮各因此翻转一次结论）。那 30 行的原始输出一直在仓库外。已把它**逐字转存**为 `reports/upstream-c-tests-log.md`（31 行 / 1215 B /
sha256 `71f99ca645941e2c…`，末行 `FILES=30 TEST_PROCS=232 FAILED_FILES=0`），
三处引用改指该文件，并在每处写明「create 日志只有汇总行」的原因。

**P3-1 悬空指针**：`reports/conan-create-log.md` 头部原指向
`manifest.yaml` 的 `validation.*.command`，该段不存在（只有 `verification:`）。
已改指 `verification:` 段，并顺手修掉 `reports/conan-verify-report.md` 中由工具硬编码
文件名产生的同类悬空指针（`📄 日志: …/conan-create.log` → `conan-create-log.md`）。

**P3-2 包内 URL 形态不一致**：`manifest.yaml` 的 `source.url` 仍是 codeload 形态，
与 `conandata.yml`（archive 形态、实际使用且锚定 sha256）不一致。已按实际使用的形态
对齐（两形态 tarball sha256 实测相同 `3cc205d2…f5b3`）。

**P3-3 未锚定的旧统计**：`notes.md` 的仓库 URL 形态存量 1637/191/254 按文档所载命令
复测为 **1714/204/265**（2026-09-11 在 `upstream/main` 上重测），已在原处订正并标明
更正日期与命令。

**P3-4 不可现场复核的缓存目录名**：本文档原写实测包目录/构建目录为
`p/b/wuffs3d82577138280/…`，既与入库日志记录的本轮目录（`wuffs3be1f9f0633cf`）不符，
又已随清缓存消失。已改为**glob 定位口径**并明确「分片目录名逐轮重建、不要在报告里
找固定名字」，判据只保留与目录名无关的量（文件清单、退出码、ELF 属性、sha256）。
本轮构建目录字符串直接取自入库日志自身（可 `grep -n 'Build folder\|Package folder'
reports/conan-create-log.md` 复核）。

**P3-5 复核命令使用只读路径**：`test_package/MANIFEST.yml` 的手工复核命令写
`-o /tmp/t`，而本设备 `/tmp` 是只读挂载（`touch /tmp/x` → `Read-only file system`），
逐字执行会 30 次全部链接失败并**静默得到空输出**。已改为
`T="${TMPDIR:-$HOME/tmp}/wuffs-count"` 并加注该坑。

**P3-6 列表项引号形态**：审计称本文档镜像中间态 diff 写成无引号列表项。
**该项不成立**：所引行（第 402–405 行）三个列表项均带双引号，与仓库主流形态一致
（`upstream/main` 实测带引号列表项 2024、裸形式 3）。故未改动内容，在此记录不复现。

**P3-7 元数据时间陈旧**：`manifest.yaml` 的 `conan_create_date` 为
`2026-09-10T18:40:00`，与采信轮日志的 `Exported:` 行不符。已改为**当前采信轮**的
导出时刻 `2026-09-11T13:21:38Z`（`grep -m1 'Exported: wuffs' reports/conan-create-log.md`
可复核；该字段随采信轮推进而更新，不锚定历史轮）。

**因 P2-1 修复而必须连带完成的一步（rrev 前移）**：`conanfile.py` 的内容计入 recipe
revision，改动注释同样会前移 rrev（`fcd12342…` → **`123c2bd7…`**）。因此
`reports/conan-create-log.md` 这份逐字留档已用**本轮**（`123c2bd7…`）的清缓存日志
重新生成，保证「留档头部声明的 rrev == 当前 HEAD 的导出 rrev」；否则会留下
「证据日志属于被取代的配方版本」这一实质缺陷。同轮 `test_package/MANIFEST.yml`
与 `notes.md` 中新引用的 `reports/upstream-c-tests-log.md` 已随本 PR 提交。

**P3-8 工作区残留**：`conandata.yml.orig`、`conandata.yml.ghfast-bak`、
`test_package/build/`、`test_package/CMakeUserPresets.json`、`.build-cache/` 均为
工具副作用（全部被 `.gitignore` 覆盖、不在提交面）。
**如实更正**：本轮清理后，紧接着的 T3 清缓存重验（`conan-verify` + 构建 `test_package`）
又把其中四项**重新生成**了一遍——`conan_verify.py` 的 E017 注入每次 create 都会写
`conandata.yml.orig`/`.ghfast-bak`，`cmake_layout` 每次都会落 `test_package/build/` 与
`CMakeUserPresets.json`。所以「清理」不是一次性动作，而是**收尾固定步骤**：凡在最终 SHA
上跑过 `conan-verify`/构建，就必须在派发审计与收尾前再清一次，否则审计会（正确地）报
「声称已删除但仍在盘上」。更正后的表述以此为准。

**未复现项**：除 P3-6 外，审计提到的「`refresh-patch --auto` 生成过程与
`.ci-result.json` 的 `integrity_hash` 无法独立复算」「文档所述两 TU 各自
`WUFFS_IMPLEMENTATION` 重复符号实验未复现」两条，均属审计方声明无法复现而非缺陷
认定，本报告不据此改动任何结论。

---

## 13. W4 第十轮审计（修复后复审：P2×2 / P3×4）处置

第十轮独立审计对被审 SHA `7878e229` 的结论是 `verdict=pass`（**P0=0、P1=0**），
并逐项复核了第 12 节的 10 项修复：**8 项改对、1 项（P3-6）确认上一轮判定本身不成立、
1 项（P3-8）没改到位**（原因见第 12 节该条的如实更正），另新发现 6 项。处置如下。

**P2-1 逐字留档的抽取口径有歧义（`conan-create-log.md`、`upstream-c-tests-log.md`）**：
审计按「额外剥掉结尾空行」的口径抽取，得 32735 B / 355 行 / sha256 `44ae801d…`，与头部
声明的 32736 / 356 / `2706666a…` 差 1 字节。**该 1 字节差异属抽取口径歧义，不是内容篡改**：
两文件按 CommonMark 语义（围栏之间全部字节）抽取时与仓库外原件**逐字节相同**（已实测，
`inner == raw` 为 True）。根因是原文以空行结尾（`…ed\n\n`），而「空行算内容还是算围栏前
分隔」在两种实现下不同。已把**确切的抽取命令**写进这两个文件的头部（取 ```` ```text ````
之后、最后一个 ```` ``` ```` 之前的全部字节，不再剥末尾换行），歧义即消除。

**P2-2 上一轮 P2-2 的修复范围不完整**：审计指出 `manifest.yaml` 的 `tests.upstream_not_run`
与 `notes.md` 第 158 行仍写「逐文件与实跑日志 30/30 吻合」，且 `manifest.yaml` 全文未引用
新证据文件。**该意见成立**——我上一轮只改了三处（`notes.md` 的命令行注释块、
`test_package/MANIFEST.yml`、本文档第 8 节），漏了这两处。现已把两处改为指向
`reports/upstream-c-tests-log.md`，并各自写明「conan create 日志因配方重定向 stdout 而只有
汇总行」。`grep -rn '实跑日志 30/30' manifest.yaml notes.md` → **无输出**（该无锚点表述已在
两个规范文件内清零）；本文档本节因引用原句、以及 `reports/audit-result.json` 的审计记录里
仍会出现该字面，故不写「全仓 0 命中」。

**P3-DOC-RREV rrev 判据不成立**：留档头部把 create 期 rrev 表述为「当前 HEAD 导出 rrev」，
而 `scripts/ohc/conan_verify.py:561-576` 会在 create 前把工作区 `conandata.yml` 的
`https://github.com` 就地替换为 `https://ghfast.top/https://github.com`、create 后回滚，
故该 rrev 对应**镜像态** conandata.yml（审计在隔离 `CONAN_HOME` 下复算得独立佐证）。
已把判据改为如实表述：该 rrev 是 **create 期物料**指纹，与「HEAD 官方态 conandata.yml +
HEAD conanfile.py」单独 export 的 rrev **本就不同**，属工具行为；本报告只用它做
**跨轮可比性**判据（同为镜像态时 rrev 相同 ⇔ 导出物料未变）。**该现象第九轮已存在，
非本轮引入**；已作为工具缺陷写入任务反馈。

**P3-DOC-CMD 自述复核命令的取值（三轮反复，根因已定位，最终口径如下）**：第十轮指出
本文档原写「未限定范围的 `grep -c` → 0」而当时实际返回 1（命中留档头部说明句里的同一串
字面）；第十一轮又指出我改成「→ 1」后，因同一提交改写了那段说明，**该值又变回 0**——
即**这个计数随留档文字本身改写而翻转**。根因是自指：为了说明一条 grep 的结果，必须把被
检索的模式写进被检索的文件里。

最终口径（已同时写入 `reports/conan-create-log.md` 头部）：**判据必须限定在正文代码块内**，
即「抽取该文件的 fenced 代码块 → 在其中计数」，本 SHA 实测为 **0**（对应「该轮 `conan create`
日志正文确实没有逐程序 PASS 行」这一事实）。不再使用「对整份文件计数」的写法。

**P3-DOC-META 证据的生成方式写错**：`upstream-c-tests-log.md` 原写「手工 clang 循环」，
实际由探索期脚本 `run-c-tests.sh`（任务私有、仓库外）产生——日志里的 `clang15` 标签与
两空格对齐是该脚本的输出格式。已在该文件内补「这份输出是怎么产生的」一节，如实指向脚本，
并与 `native-build-test.md` 第 103–104 行、本文档第 8 节的记载对齐。

**P3-8 工作区残留（第 12 节已如实更正）**：见上。

**未采纳/不适用**：审计另提「`g_tests[]` 内含 `#ifdef WUFFS_MIMIC` 的文件共 28 个」无法
独立判定（文件级字符串搜索得 30/30）。该数字来自「整文件带宏预处理会失败的 10 个」这一
实测子集的补集推导，属历史错误（242）的成因解释，不影响任何计数与结论；本报告保留原表述
但不据此改动主结论。

---

## 14. W4 第十一轮增量复审（P2×1 / P3×3）处置

第十一轮对被审 SHA `42157fa96e` 做 T2 增量复审：`verdict=pass`（**P0=0、P1=0**），
并逐项确认第 13 节的 6 项修复中 **5 项改对、1 项（P3-DOC-CMD）没改对**，另新发现 4 项。
处置如下。

- **P3-DOC-CMD（没改对，本轮重新定位根因）**：见第 13 节该条的「三轮反复，根因已定位」段。
  结论：判据改为**限定在正文代码块内计数**（实测 0），不再使用对整份文件计数。
- **N1（P2，本文件数字串了姊妹文件的）**：`reports/upstream-c-tests-log.md` 新增段落里写
  「另一种口径得到 32735 B / 355 行」，那是 `conan-create-log.md` 的数；本文件同口径实为
  **1214 B / 30 行 / sha256 `3a2c9a55…`**。已改本文件自己的数字，并注明姊妹文件为
  32735/355、两处不可混用。
- **N2（P3，锚点回退）**：上一轮重新生成 `reports/conan-create-log.md` 时，把「本日志没有
  逐程序 PASS 行、明细见 `upstream-c-tests-log.md`」整段丢失，导致该文件 0 引用证据文件。
  已恢复该锚点，并写明 `notes.md`、`test_package/MANIFEST.yml`、`manifest.yaml` 的对账结论
  均指向它。
- **N3（P3，自述命令不可复现）**：第 13 节原文「全仓 `grep '实跑日志 30/30'` 现为 0 命中」
  字面不成立（该字面会出现在本节自身与被 gitignore 覆盖的 `audit-result.json` 里）。已改为
  限定范围的命令：`grep -rn '实跑日志 30/30' manifest.yaml notes.md` → 无输出。
- **N4（P3，归因不精确）**：`upstream-c-tests-log.md` 原把 `clang15` 标签与列对齐归因给脚本，
  实为上游测试框架所产。已补「归因（勿混淆两层）」段：脚本只做「逐个编译 + 运行 + 原样收集
  stdout / 追加汇总」，`PASS (N tests)` 行的格式来自 `test/c/testlib/testlib.c:451` 的
  `printf("%-16s%-8sPASS (%d tests)\n", g_proc_package_name, g_cc, …)`（`clang15` 是 testlib
  自报的编译器名，设备 `clang --version` 为 15.0.4），列宽是 16/8 而非「两空格」。

**累计教训（写入任务反馈）**：本任务第 10–11 两轮的返工全部集中在同一类——
**用文字描述一条命令的结果时，描述本身改变了命令的结果**（自指）。凡在文档里声明
「某文本不存在 / 计数为 N」，必须把检索范围限定到与断言文本不重叠的区域（本处即代码块内），
否则结论会随文档改写反复翻转。
