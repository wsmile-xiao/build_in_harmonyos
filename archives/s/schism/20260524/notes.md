# schism 20260524 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

autotools：`./configure --prefix=$DEFAULT_PREFIX` → `make` → `make install`（由 `conan create` 驱动）。
补丁 0001/0002 更新 `config.guess`/`config.sub` 以识别 `aarch64-unknown-linux-ohos`；补丁 0003/0004 处理上游 `-Werror` 严格告警；补丁 0005 处理 HMDFS 临时目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 上 `./config.status: line 608: ./confXXXXXX/subs1.awk: Permission denied`，随后 `configure: error: could not setup config files machinery` | HMDFS 上 `(umask 077 && mktemp -d "./confXXXXXX")` 建的临时目录对 CI 构建用户不可写（知识库 E011 同类） | 补丁 `0005-configure-avoid-mktemp-hmdfs.patch`：改用 `mkdir -p "${TMPDIR:-$HOME/tmp}/conf$$-$RANDOM"`，兜底分支去掉 `umask 077` |

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

- 本机 HMDFS 会把 `mkdir` 生成的目录强制为 `drwxrws--x`（group 可写），而 `mktemp -d` 的路径在 CI 上不可写 → 构建脚本内不要用 `mktemp -d` 建临时目录（见补丁 0005）。

## CI 修复记录（build #65783，第 1 轮）

- 失败现象：`./config.status: line 608: ./conflhcmJG/subs1.awk: Permission denied` → `configure: error: could not setup config files machinery`（CI build #65783，失败评论 id=192377309）
- 根因：与知识库 E011 同一机制——HMDFS 上 `config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建的临时目录对 CI 构建用户不可写；`config.status` 第 608 行 `echo 'BEGIN {' >"$ac_tmp/subs1.awk"` 正是写该目录，失败后 configure 直接中断。
- 修复：`patches/0005-configure-avoid-mktemp-hmdfs.patch`（只改构建脚本，未触碰被编译源码）
  - 主路径 `tmp="${TMPDIR:-$HOME/tmp}/conf$$-$RANDOM" && mkdir -p "$tmp"`（弃用 `mktemp -d` 与 `umask 077`）
  - 兜底分支 `(umask 077 && mkdir "$tmp")` → `(mkdir "$tmp")`
  - 临时目录优先落在 `$TMPDIR`/`$HOME/tmp`（与 `ci/conan/*.sh` 同一处可写约定），失败时回落构建目录
- 本地验证：
  - `patch -p1 --dry-run` 与实际应用 RC=0；`sh -n configure` 通过；代码路径内 `umask 077` 残留 0 处
  - 补丁后代码段在 `TMPDIR` 已设/未设两态下均能创建并读回 `subs1.awk`
  - W3 本地 CI 模拟 `rc=0`：`L0/L1/L2/L5=pass`、`Success: 1/1`；日志出现 `configure: creating ./config.status` / `config.status: creating Makefile` / `creating build-config.h`（原失败环节已通过）
- 局限：本机 HMDFS 把 `mkdir` 与 `mktemp` 都强制成 `drwxrws--x`（group 可写），无法本地复现 CI 上 mktemp 目录不可写这一态，最终判定以 CI 重跑结果为准。
---

**编译结束**: 2026-09-30 20:00
**最终状态**: built

---

## 四、上游测试面清点（R51 三步法台账）

**Step1 清点**（源码包 `schismtracker-20260524.source.tar.gz`，
sha256 `3b211da6ea8f1db966bfc1c85e1774bda6420c5b5d24dadea9e9463fd9f66a18`）

| 位置 | 文件数 | 内容 |
|---|---|---|
| `test/` | 7 | harness 框架（assert / harness / testresult / log / index / tempfile / vmem） |
| `test/cases/` | 12 | 11 个用例源 + `version-values.h` 数据头 |
| 合计 | 19 个文件 + 1 个目录条目 | 本机解压源树实测 `N_TEST_FILES=20` |

用例注册表 `include/test-funcs.h`：字面 `TEST_FUNC(...)` 注册 **144** 条
（其中 `#ifdef SCHISM_WIN32` 平台专属 4 条 → 非 Windows 口径 140 条），
另有 `TEST_FUNC_BLIT` ×7 / `TEST_FUNC_BLIT_SC` ×9 共 16 处宏调用在编译期展开，
展开后 video 用例族 **158** 条注册（BLIT→2 条、SC→2×4×2=16 条）。
**上游用例数 N = 302**（注册表条目实测口径；非 Windows 口径 298、未定义特性宏口径 293）。
平台审查脚本口径 141 亦如实登记、未少报（见第五节 rule4 行），本文件与
`MANIFEST.yml` / `manifest.yaml` 统一取实测值 302。

复现命令（解包源码树根，clang 用项目内置工具链）：

```bash
clang -E -P -x c -D'TEST_FUNC(x)=M(x)' include/test-funcs.h | grep -o 'M(' | wc -l   # 293（无特性宏）
# 加 -DHAVE_MMAP -DUSE_ZLIB -DUSE_BZIP2 -DUSE_LZMA -DUSE_ZSTD → 298；再加 -DSCHISM_WIN32 → 302
```

**Step2 实跑**：未执行。根因——`configure.ac:224-226` 的 `--enable-tests` 默认 `no`；
`Makefile.am:99-100` `if BUILD_TESTS → bin_PROGRAMS += schismtrackertest`；
全树无 `TESTS =` 目标（`make check` 不触发套件，测试程序须显式构建后手工执行）。
141 条用例逐项 `not_executed_reason` 见 `test_package/MANIFEST.yml`。
（第 3 轮修正：该句口径已统一为 **302 条注册用例**，见第六节。）

**Step3 回填**：`test_package/MANIFEST.yml`（逐项清单）+ 本文件 + 版本级
`manifest.yaml` 的 `upstream_tests` 段。鸿蒙侧消费者用例（`test_package/test.c`，
popen 真实执行包内 `bin/schismtracker`）2 用例 / 4 断言点，实跑 2/2 通过。

## 五、人工审核修复记录（第 2 轮）

| 规则 | 结论 | 根因 | 修复 |
|---|---|---|---|
| rule1 | FAIL | PR 描述未按模板给出「上游测试用例修改说明 / 补全测试用例说明」复选框段 | 按 `templates/积分赛事PR模板.md` 重写描述：补齐字段 + 两张统计表 + 两个复选框段 |
| rule4 | FAIL（少报） | 描述声明上游 N=0，平台审查脚本实测 N=141 | 描述与 `MANIFEST.yml` / `manifest.yaml` / 本文件统一改为 N=141，并附可复现清点口径（字面 144 / 非 Windows 140） |
| rule8 | FAIL | 由 rule4 的「上游 N=0」错误声明连带触发（该规则仅在 N=0 时生效） | 随 N=141 的如实登记自动消解，无需额外改动 |
| rule6 | FAIL | 最新提交晚于最近一次 AI 检视，且此前 `/ai review` 因平台临时故障未产出结论 | 代码/文档修复后由维护者重新触发 `/ai review`（本机无 CI/检视触发权限） |

**同时修正的失真点**：`test_package/MANIFEST.yml` 原为未填写的模板（含 `<TODO:…>`
占位与 `assertion_count: <TODO: 断言数>`）；`manifest.yaml` 原为含 `{software}` /
`{BUILD_SYSTEM}` 占位符的空模板（补丁、依赖、哈希均未填）；`conanfile.py` docstring
误称「仓库无自动化测试套件」——三处均按实测重写。

## 六、本地复核修正记录（第 3 轮，平台故障期本地 AI 检视）

第 2 轮修复后本地复核（`clang -E` 展开注册表 + 逐文件 `cases` 交叉核对 + 知识库拓展
产出物自检）发现并修正以下问题：

| # | 级别 | 问题 | 修正 |
|---|---|---|---|
| 1 | P1（R51 少报） | 三处元数据把 video 宏族的 **16 处宏调用**当成 **16 条用例**，video.c `cases: 16` 与逐文件求和 160 均低于注册表实际条目数 | video.c `cases` 16→**158**，逐文件求和 302；`test_count` / N 141→**302**（非 Windows 298、无特性宏 293），三处文件 + 复现命令统一 |
| 2 | P1（自相矛盾） | `N=141` 与同段自报的「字面 144 / 非 Windows 140」互相矛盾（141 > 140） | 统一为可复现实测口径 302，平台口径 141 保留登记并注明来源 |
| 3 | P1 | 知识库拓展 `sample-verification.json` 的 `evidence_log` 写死本机绝对路径 `/storage/Users/currentUser/...`，违反拓展自带约束「无本地绝对路径」 | 改为相对文件名；`reproduce.sh` 写结果 JSON 时改用 `basename` |
| 4 | P1（E002） | README / `reproduce.sh` 示例命令用 `/tmp/werror-repro`，本平台 `/tmp` 只读 | 示例改 `$HOME/tmp/werror-repro` 并注明 E002 |
| 5 | P1（R39） | `conandata.yml` 的 `sources.url` 首条为 `gh-proxy.com` 镜像 | 只保留官方源（CI 侧自动追加镜像 fallback） |
| 6 | P2 | `detect_werror.py` 三条源码正则不分文件类型套用（`-Werror\b` 也命中原生 `configure`），实测 51 命中中 29 条为误报；`detail` 截断 50 无提示；`--json` 形同虚设 | 规则按文件名分派（configure / configure.ac / Makefile.am / CMakeLists.txt 各取适用规则）；新增 `rule_counts` 与 `detail_truncated`；`--json` 生效（默认人读摘要） |
| 7 | P2 | 【知识库扩展】PR 缺知识图谱条目，扩展无法被 engine 匹配 | 新增 `knowledge/drafts/DRAFT-werror-autotools.kv` + 配套 `.md` |
| 8 | P3 | `manifest.yaml` 注释称 `patches/autotools/config/*`「由补丁头引用」，实际补丁为自包含 diff、配方不引用 | 注释更正为「人工比对留存副本（CI 不消费）」 |

本地复核同时确认：5 个补丁在 20260524 源码树上 dry-run / 累积 apply 全部 rc=0；
`conan create` 在 head 树上全流程通过（包 revision 已创建、`test_package` 消费者用例
`--version` / `--help` 2/2 PASS）。

### 六.1 R8 平台宏例外说明（补丁 0001 的 `__OHOS__`）

补丁 `0001-update-config-guess-ohos.patch` 在 config.guess 的 **libc 探测 C 探针**
（GNU config.guess 内嵌、由 `$CC` 编译的 `#if defined __UCLIBC__ … ` 片段）中新增
`#elif defined(__OHOS__)` 分支。按 `references/iron-rules.md` R8「patches/ 补丁文件中
默认禁止引入平台宏，例外（如 libc 探针）须在 PR 说明理由」，本条即为该例外：

- **为何必须用平台宏**：该探针是 config.guess 内嵌的预处理器分支，运行时机在
  `AC_CANONICAL_HOST` 之前，此时既无 `config.sub` 结果也无平台配置变量可用；
  唯一可判据是编译器预定义宏（OHOS clang 定义 `__OHOS__`）。
- **与既有知识一致**：知识条目 `E007`（config.guess 无法识别 HarmonyOS）登记的
  canonical 方案 `scripts/patch-autotools-ohos.pl` §2.1 LIBC 检测即为同一写法，
  本补丁与该方案同源，不引入新口径。
- **影响面**：仅构建脚本（shell + 内嵌 C 探针），不触碰被编译源码的任何头/源文件；
  非 OHOS 平台该分支不参与（`#elif` 且前置分支更早命中）。

其余 5 个补丁（0002 config.sub / 0003、0004 去 -Werror / 0005 临时目录 /
0006 补齐 release tarball 漏发的 `include/test-vmem.h`）**零平台宏**，全部走 POSIX 兼容方式。

## 七、第 4 轮：上游套件真实接入 + SDL2 直链根因修复（平台人工审核 FAIL 修复）

### 7.1 触发

PR #14041 收到 47 条人工审核意见，两条 `VERDICT=FAIL`：

| 评论 | 审核人 | FAIL 项 |
|---|---|---|
| `192417511`（2026-10-02T10:48:07） | bengbeng2345 | rule1（上游测试用例修改说明复选框解析不到）、rule4（少报：实测 N > 声明）、rule6（最新提交晚于最近 AI 检视）、rule8（上游 N=0 且适配后 M=0 未补增测试） |
| `192422944`（2026-10-02T14:29:53） | Septest | rule4（少报：上游实测 N=144 > 声明 N=141），其余全 PASS |

共同核心诉求：**上游用例不仅要清点，还要真实执行并如实回填**（R51 三步法 Step2 此前记「未执行」）。

### 7.2 根因链（三层，缺一即无法真实执行）

1. **上游未把套件接入 `make check`**：`Makefile.am` 的 `TESTS` 为空 → `make check` 不触发任何用例；
   `configure.ac:224-226` 的 `--enable-tests` 默认 `no` → 默认连 `schismtrackertest` 都不构建。
2. **release tarball 漏发 `include/test-vmem.h`**：上游 git 同 tag 存在该文件（本机实测
   `raw.githubusercontent.com/.../include/test-vmem.h` → HTTP 200，`test/test-vmem.h` → 404），
   但官方 `*.source.tar.gz` 未收录 → `test/vmem.c:26` 报 `fatal error: 'test-vmem.h' file not found`
   → 补丁 **0006** 以补丁形式补齐（内容取自上游同 tag，仅文件尾部补换行）。
3. **SDL2 运行时 dlopen 崩溃（段错误）**：上游默认走 `sys/sdl2/init.c:56
   library_load("SDL2-2.0", 0, 0)`，即运行时 `dlopen("libSDL2-2.0.so.0")`；而制品仓
   `sdl2/2.30.10` 在 OHOS 档位**只提供静态 `libSDL2.a`**（包内 `lib/` 无任何 `.so`）
   → dlopen 必然失败 → `sdl2_*` 后端函数指针全为 NULL → `schism/timer.c` 的
   `timer_ticks()` 解引用空指针 → **SIGSEGV**（批量 exec 退出码 `139`；
   `NEEDED` 只有 `libc.so`，可证测试二进制未链接 SDL2）。
   **同一根因使 `schismtracker` 本体在 OHOS 上启动即崩**，不只是测试问题。

定位手段：在 `timer_ticks()` 前后插检查点打印（本机 `ptrace` 全禁，`gdb` 不可用），
确认 `CK1-pre-timer_ticks` 已打印、`CK2` 未达 → 崩在 `timer_ticks()` 内。

### 7.3 修复

| # | 改动 | 位置 |
|---|---|---|
| 1 | 新增 `--enable-sdl2-linking`：配置期直链静态 SDL2，取代运行时 dlopen | `conanfile.py` `generate()` |
| 2 | 显式传入 `SDL2_CFLAGS`/`SDL2_LIBS`（路径取自依赖 `cpp_info`，R49）；`.pc` 不可靠——`sdl2.pc` 记 `prefix=/`（打包机绝对路径不可迁移） | `conanfile.py` `generate()` |
| 3 | 新增 `--enable-tests` 构建 `schismtrackertest`，并在 `build()` 内**显式执行**（上游 `TESTS` 为空，`make check` 无效）；用例失败即构建失败，不掩盖不跳过 | `conanfile.py` `build()` |
| 4 | 执行时 `TMPDIR` 固定到构建目录内（鸿蒙 `/tmp` 只读，E002）；输出落 `ohc-upstream-tests.log` 并把尾部打进构建日志 | `conanfile.py` `build()` |
| 5 | `package()` 剔除 `bin/schismtrackertest`（测试二进制不随包发布） | `conanfile.py` `package()` |
| 6 | 补丁 `0006-add-missing-include-test-vmem.patch` + `conandata.yml` 登记 | `patches/` + `conandata.yml` |

### 7.4 实测结果（本机 OHOS aarch64 / clang 15）

```
TEST: test_bshift_arithmetic ... （逐条）
Results: 294 passed, 0 failed
Elapsed: 8.984 seconds
```

- **执行 294 条 / 通过 294 / 失败 0**，耗时 8.984s。
- `294 = 302（注册表条目）− 4（#ifdef SCHISM_WIN32 平台专属：charset 2 + slurp 2）
  − 4（特性开关未启用：gzip / bzip2 / xz / zstd 未探测到对应库）`。
- 逐文件执行数（求和 = 294）：video 158 + str 69 + bits 19 + config-parser 19 +
  mplink 13 + version 5 + charset 3 + slurp 5 + sanity 1 + util 1 + disko 1。
- 口径统一：**注册 302 / 实跑 294 / 通过 294**；平台审查脚本口径 141 与字面 `TEST_FUNC`
  144 一并登记（均低于实测口径），不存在少报。

### 7.5 台账回填

| 文件 | 回填内容 |
|---|---|
| `test_package/MANIFEST.yml` | `upstream_test_in_build: true`、`upstream_test_command`、`upstream_executed_count: 294`、`upstream_passed_count: 294`、`upstream_failed_count: 0`；逐文件条目 `executed: true` + `execution_note`（含条件注册未跑条数与原因） |
| `manifest.yaml` | `configure_options` 增两项；`upstream_tests.executed_count/passed` 294；`patches_applied` 增 0006；`patch_generation.patches_count` 6；`knowledge_gained` 增 SDL2 静态库 dlopen 陷阱 |
| 本文件 | 本节 |

### 7.6 余下需平台侧配合的项

- **rule6**（最新提交晚于最近 AI 检视）：本轮修复提交后需重新触发 `/ai review`
  （本机无触发权限，平台机器故障期由维护者执行）。
- **rule1**（复选框解析）：第 5 轮 PR 正文按模板重写「上游测试用例修改说明 / 补全测试用例说明」
  复选框段。
- **rule8**：上游 N 已非 0 且套件已真实执行（294/294），随 rule4 一并消解。

