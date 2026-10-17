# alsa-lib 1.2.14 适配笔记

## 编译环境
- 构建系统: autotools（官方 release 归档自带 `configure` / `Makefile.in` / `config.h.in`，不重新 autoreconf）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 目标: os=OHOS, arch=armv8 (aarch64)，profile `ci/conan/profiles/ohos-aarch64`
- 本机即 OpenHarmony PC 目标机（非交叉），`conan create` 的 test_package 与上游测试都真实执行
- 结果: built（shared / static 两种产物形态的 `conan create` 均 rc=0；上游 `make check` 2/2 PASS；test_package 11/11 PASS）

## 源码与依赖前置
- 上游源: 官方 `https://www.alsa-project.org/files/pub/lib/alsa-lib-1.2.14.tar.bz2`
  sha256 `be9c88a0b3604367dd74167a2b754a35e142f670292ae47a2fdef27a2ee97a32`（1115517 字节，归档时间 2025-04-15）。
  1.2.14 为官方正式发版（同目录下 1.2.10~1.2.16.1 均在册），非预发布。
- 归档内唯一符号链接 `alsa-lib-1.2.14/include/alsa -> .`，与 1.2.16.1 完全一致
  （配方 `_extract_official_source()` 的断言仍成立）。
- 依赖（W0）: 本配方族**无任何第三方 Conan 依赖** —— `conanfile.py` 无 `requirements()`
  / `requires()` / `tool_requires()`；`configure` 阶段显式 `--disable-python --disable-mixer-pymods`
  关掉唯一的外部依赖面(python 绑定)。libc/POSIX、`m`、`dl`、`pthread`、`rt` 均为目标系统能力。
  `bash ci/scripts/preflight_check.sh alsa-lib/1.2.14` → `[OK] 预检通过（无依赖需要检查）`，rc=0。
- 制品仓连通性实测（证明 W0 不是"因为查不到所以过"）：`conan download alsa-lib/1.2.16 -r=ohpcd --only-recipe`
  / `alsa-lib/1.2.16.1` / `zlib/1.3.1` 均成功返回 revision；对不存在的 `alsa-lib/9.9.9.9`
  返回 `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`（该 remote 的 404 文案）。
  据此两点结论：① remote 可用；② **1.2.14 在制品仓中尚不存在**，版本号未被占用（R37/L0j 无冲突，无需 `.N` 后缀）。
- **无 R36 阻塞**：没有任何依赖需要 `--build=missing` 或本地缓存绕过。

## 与历史归档的关系（W0b 核验）
仓库已有 `alsa-lib/1.2.12`（历史非 Conan 归档）、`1.2.16`、`1.2.16.1`（均为同一配方族的 Conan 适配）。
本次按 W0b 逐项比对：

| 项 | 1.2.16 / 1.2.16.1 | 1.2.14（本次） | 结论 |
|---|---|---|---|
| 上游测试边界 | 2 个注册 Automake 用例 + 19 个 build-only 程序 | **同** | 4 个边界文件 SHA256 逐一相等（见 `reports/upstream-test-inventory.md`） |
| `test/Makefile.am` 等 4 文件 | — | 字节相同 | 上游测试面未变，可直接沿用同一统计口径 |
| `include/alsa -> .` 唯一软链接 | 是 | 是 | 源码解包断言沿用 |
| `versionsort64` 处理 | 上游已自带 `!defined(__OHOS__)` | **1.2.14 尚无**（1.2.15 起才有） | 需新增补丁 `0008`（逐字节回移植上游写法） |
| 补丁集 | 7 个 | 8 个（多 `0008`；`0003/0005/0006/0007` 需按 1.2.14 行号重生成） | 见下 |

历史踩坑比对：1.2.16.1 的 7 个补丁语义在 1.2.14 上全部必要（`config.guess`/`config.sub` 三元组、
libtool 版本化 so、pthread_cancel、materialized include、HMDFS umask、/dev/full）。逐条按 1.2.14
源码重生成，未偏离历史结论；唯一新增是 `0008`（1.2.14 早于上游修复）。

## 补丁集（8 个，全部 patch_type=portability）

| # | 文件 | 目标 | 依据 |
|---|---|---|---|
| 0001 | `config.guess` | 识别 HarmonyOS 内核 → `aarch64-unknown-linux-ohos` | E007 |
| 0002 | `config.sub` | 接受 `linux-ohos*` 三元组 | E072 |
| 0003 | `src/Makefile.am/.in`、`src/topology/Makefile.am/.in` | 把 `-version-info` 提为可覆盖变量，使 `make ... ALSA_LIBTOOL_VERSION_FLAGS=-avoid-version` 产出**无版本号** `libasound.so` / `libatopology.so` | E330/E331（版本化软链接在 HMDFS 上不可用）、E228 |
| 0004 | `configure.ac/configure`、`include/config.h.in`、`test/pcm-multi-thread.c` | 先 `AC_CHECK_FUNCS([pthread_cancel])`，再 `#ifdef HAVE_PTHREAD_CANCEL` 守卫调用 | E127 |
| 0005 | `configure.ac/configure` | OHOS 上不建 `include/alsa` 软链接，改用已物化的真实目录（缺失则报错） | E050 |
| 0006 | `configure` | `config.status` 临时目录 `umask 077` → `022` | E129 / E136 |
| 0007 | `src/pcm/pcm_null.c` | capture 打不开 `/dev/full` 时回退 `/dev/zero` | 本机实测 `/dev/full` 不可读 |
| 0008 | `src/ucm/parser.c`、`src/conf.c` | `_GNU_SOURCE` 分支排除 `__OHOS__`，避免使用不存在的 `versionsort64` | 本次新增（libc 探针） |

**补丁生成与验证方式**（三点都做了，且可复现）：
1. 以**累积态**生成：按应用顺序，第 N 个补丁的上下文行号基于"已应用 1..N-1"的文件状态计算
   （Conan 的 `patch()` 用 patch_ng，**不做 fuzz**，行号偏移会直接失败——这一点是本次踩到的坑，见下）。
2. 生成后逐补丁断言每个 hunk 的 `@@ -start` 与前置文件该行内容一致。
3. 每补丁在纯净副本上用宿主 `patch -p1` 实跑，并断言**应用后文件内容 == 预期编辑语义**（防止模糊落点）。
   8/8 VERIFIED；随后在纯净 1.2.14 树上按序应用 8 个补丁，8/8 rc=0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 修复 | 重新验证 |
|---|------|------|------|----------|
| 1 | 沿用 1.2.16.1 的 `0004` 时 `conan create` 报 `hunk no.1 doesn't match source file at line 55`（`configure.ac`） | 两个原因叠加：① 1.2.14 中 `AC_CHECK_FUNCS([uselocale])` 在第 53 行、1.2.16 在第 55 行；② 宿主 toybox `patch` **会容错偏移**（rc=0 假通过），而 Conan 用的 patch_ng **不容错** | 不再复用历史补丁，改为按 1.2.14 源码用 difflib 生成全部补丁，并显式校验 hunk 行号 | 8 个补丁在纯净树上按序应用 8/8 rc=0；后续 `conan create` 通过全部 `Apply patch` |
| 2 | `src/ucm/parser.c:2936: use of undeclared identifier 'versionsort64'` | OHOS libc 提供 `scandir64`/`alphasort64`/`struct dirent64`，但**不提供 `versionsort64`**；`configure` 检测到 `_GNU_SOURCE` 于是选了它 | 新增补丁 `0008`：把 `_GNU_SOURCE && !…` 守卫加上 `!defined(__OHOS__)`（与上游 1.2.16 逐字节一致） | 探针 `probes/dirent64_symbols.c` 编译对照；重建通过 |
| 3 | 修完 `parser.c` 后 `src/conf.c:4149` 报同一错误 | 同类代码在 1.2.14 里有**两处**（`parser.c` 与 `conf.c`），首轮只改了一处 | 把 `0008` 扩为两文件（上游 1.2.16 同样两处都改） | 两处均通过编译 |
| 4 | 补丁 0005 首轮行号取自纯净树，应用时报 `doesn't match at line 756` | 前置补丁 0004 已向 `configure.ac` 插入了 1 行、向 `configure` 插入了 7 行，后续补丁的上下文整体后移 | 补丁生成器改为**累积态**生成 | 0005 的 hunk 头变为 `@@ -756,7 +756,11 @@` / `@@ -15665,7 +15665,11 @@`，通过 |
| 5 | 工作区 `archives/l/libXext/README.md`、`manifest.yaml` 出现莫名改动 | `core.ignorecase=true`，`main` 同时跟踪 `libXext/` 与 `libxext/` 两条路径，磁盘上只能存在一个目录 | 与本次适配无关，全程不 `git add`、不提交（隔离处理） | `git diff` 仅这 2 个文件；最终提交白名单不含它们 |

## 上游测试入口核验与实测（R51 三步法）

**第一步 清点**：见 `reports/upstream-test-inventory.md`。上游注册入口恰为 2 个
（`test/lsb/Makefile.am` 的 `TESTS = config` + `TESTS += midi_event`），另有 19 个
`check_PROGRAMS`（只编译、不注册、不算用例）。4 个边界文件 SHA256 与 1.2.16.1 完全一致。

**第二步 真实执行**：`make check` 在配方 `build()` 内执行，因此 `conan create` **不可能绕过**上游测试。
命令与超时：

```
make -j1 check LOG_COMPILER=/system/bin/timeout AM_LOG_FLAGS=180
```

`LOG_COMPILER` 由配方改为 `_write_upstream_test_launcher()` 生成的 launcher，
使扩展名脚本与 ELF 都能被 `/system/bin/timeout 180` 包住（E228 同款处置）。

**第三步 实测统计**（两种产物形态各跑一遍，真实执行，非占位）：

| 形态 | 用例总数 | 通过 | 失败 | 跳过 | XFAIL | XPASS | ERROR | 退出码 | 日志 |
|---|---|---|---|---|---|---|---|---|---|
| shared | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | `_scratch/alsa-w0/logs/conan-create-shared.final.log` |
| static | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | `_scratch/alsa-w0/logs/conan-create-static.log` |

逐用例：

| 用例名 | 来源 | 注册方式 | shared | static |
|---|---|---|---|---|
| `lsb-config` | `test/lsb/config.c` | `TESTS = config` | PASS | PASS |
| `lsb-midi-event` | `test/lsb/midi_event.c` | `TESTS += midi_event` | PASS | PASS |

Automake 汇总原文（shared）：

```
Testsuite summary for alsa-lib 1.2.14
# TOTAL: 2
# PASS:  2
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

两个 `.trs` 终态逐行（shared/static 均同）：

```
:test-result: PASS
:global-test-result: PASS
:recheck: no
:copy-in-global-log: no
```

配方另有硬断言：`.trs` 集合必须**恰好**是 `{test/lsb/config.trs, test/lsb/midi_event.trs}`，
字段必须恰好是上表四行——多一个、少一个、失败或 `recheck=yes` 都会让构建失败。

## 消费者可行性测试（鸿蒙用例，PF3）

本次**新增的鸿蒙消费者用例是完整 11 条**（`test_package/`），实际在 OHOS 目标机上编译并执行，
不是空壳：每条都有独立的可执行文件与 180s 超时，结果逐条打印 `PASS <ID>`。

| ID | 源文件 | 覆盖 |
|---|---|---|
| AL-FUN-001 | `format_roundtrip.c` | PCM format 名/值、logical/physical 宽度契约 |
| AL-FUN-002 | `areas_silence.c` | 有界交织静音，未触碰哨兵值 |
| AL-FUN-003 | `areas_copy.c` | 带偏移的交织拷贝，未触碰哨兵值 |
| AL-FUN-004 | `null_playback.c` | null playback 配置/start/write/drain/close 生命周期 |
| AL-FUN-005 | `null_capture.c` | null capture read/drop/close 与"不得写数据"契约（依赖补丁 0007） |
| AL-FUN-006 | `topology_roundtrip.c` | 内存拓扑 manifest 构建/解码/保存往返 |
| AL-PKG-001 | `component_asound.c` | `ALSA::asound` 精确版本与包树运行时加载 |
| AL-PKG-002 | `component_atopology.c` | `ALSA::atopology` 生命周期、版本与依赖闭包 |
| AL-PKG-003 | `conanfile.py`（relocated） | 重定位后的 pkg-config 元数据 + 两个运行时消费者 |
| AL-PKG-004 | `conanfile.py`（artifact） | 产物/ABI 契约：无版本号 so、SONAME/NEEDED、静态库、静态 fPIC whole-archive 链接、头文件、配置、CMakeDeps/PkgConfigDeps、签名清单、许可证 |
| AL-PKG-005 | `feature_contract.c` | 生成的组件/插件/路径元数据与激活后的运行环境 |

实测：shared 11/11 PASS，static 11/11 PASS，日志尾行为
`validated 11 independent ALSA test-package entries`。另有 60 个公共 ABI 链接探针（只取函数地址，
`counted_as_tests: false`）在两种形态下都编译链接通过。

## 验证结果

```bash
# 1) 源码与补丁
curl -fsSL -o alsa-lib-1.2.14.tar.bz2 \
  https://www.alsa-project.org/files/pub/lib/alsa-lib-1.2.14.tar.bz2
sha256sum alsa-lib-1.2.14.tar.bz2
# be9c88a0b3604367dd74167a2b754a35e142f670292ae47a2fdef27a2ee97a32

# 2) 依赖（W0/R36）：无第三方 Conan 依赖
bash ci/scripts/preflight_check.sh alsa-lib/1.2.14      # rc=0

# 3) 真实构建 + 上游测试 + test_package（shared）
conan create archives/a/alsa-lib/1.2.14 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build="alsa-lib/*"
# rc=0；# PASS: 2 / # FAIL: 0；11/11 consumer PASS

# 4) 同上（static，验证产物形态与 fPIC 路径）
conan create archives/a/alsa-lib/1.2.14 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build="alsa-lib/*" -o "alsa-lib/*:shared=False" -o "alsa-lib/*:fPIC=True"
# rc=0；# PASS: 2 / # FAIL: 0；11/11 consumer PASS

# 5) 质量门禁
python3 scripts/ohc-run.py conan-verify alsa-lib 1.2.14
python3 scripts/ohc-run.py finish alsa-lib 1.2.14 published
```

产物（shared）: `lib/libasound.so`(1043840B) / `lib/libatopology.so`(125504B) / `bin/aserver`(47680B)，
三者均为 `DYN` ELF 且带 `.codesign`。产物（static）: `lib/libasound.a`(1764760B) /
`lib/libatopology.a`(234484B) / `bin/aserver`(699584B)，**包内无任何 `.so`**。

## 源码修改
- 仅新增 8 个 `portability` 补丁，不改上游语义、不改测试期望、不删除任何上游用例。
- 其中 2 个补丁的新增行含 `__OHOS__`（`0001` 的 `#elif defined(__OHOS__)`、`0008` 的
  `!defined(__OHOS__)`）。两者都是 **libc/三元组探测**性质的守卫，且都**逐字回移植上游自身写法**
  （1.2.16 的 `config.guess` / `parser.c` / `conf.c` 就是这些内容），按 R8 例外口径在 PR 正文明示理由。

## 知识沉淀（knowledge_gained）
- OHOS libc 有 `scandir64` / `alphasort64` / `struct dirent64`，**没有 `versionsort64`**；
  autotools 项目里凡按 `_GNU_SOURCE` 选 `SORTFUNC=versionsort64` 的代码，在 OHOS 上必须排除。
  探针：`probes/dirent64_symbols.c`（去掉 `HAVE_VERSIONSORT64` 编译通过，加上即
  `use of undeclared identifier 'versionsort64'`）。
- OHOS 的 `/dev/full` 存在但 `open(O_RDONLY)` 返回 EACCES（`ls -la` 即 Permission denied），
  `/dev/zero` 正常；依赖"capture 侧可读零设备"的代码需回退到 `/dev/zero`。
- Conan 的 `patch()` 走 patch_ng，**不做 fuzz**；而本机宿主 `patch` 是 toybox，**会容错偏移并 rc=0**。
  因此"宿主 patch 说通过"不能作为补丁可用的证据，必须校验 hunk 行号或直接在 `conan create` 里验证。
- 同一源码树里同类缺陷常有**多个站点**（本包 `parser.c` + `conf.c`），修一处不够，需全树 grep 同类模式。

## 对话记录

### 对话 #1 [2026-10-08]
- 问题: 复用 1.2.16.1 的补丁集时，宿主 `patch -p1` 报 rc=0 但 `conan create` 报 hunk 不匹配。
- 操作: 逐 hunk 复算行号与内容；用合成最小用例对照 toybox 行为；确认 toybox 容错偏移而 patch_ng 不容错；
  改为按 1.2.14 源码 difflib 生成全部补丁，并加"行号断言 + 应用后内容 == 预期"双重校验。
- 结果: 8/8 补丁 VERIFIED，`conan create` 的 `Apply patch` 阶段全部通过。

### 对话 #2 [2026-10-08]
- 问题: `src/ucm/parser.c`、随后 `src/conf.c` 报 `use of undeclared identifier 'versionsort64'`。
- 操作: 写 libc 探针编译对照，确认 OHOS 缺 `versionsort64`；比对上游 1.2.16 发现其已自带
  `!defined(__OHOS__)` 守卫；逐字节回移植为补丁 `0008`（两处文件）。
- 结果: 两处均编译通过，shared/static `conan create` 都到达 `make check` 并 2/2 PASS。

### 对话 #3 [2026-10-08]
- 问题: 补丁 `0005` 在 `configure.ac` / `configure` 上再次行号不匹配。
- 操作: 定位根因是前置补丁 `0004` 已插入行导致偏移；把补丁生成器从"对照纯净树"改为"累积态生成"。
- 结果: `0005`/`0006` 的 hunk 头随累积态更新，按序应用 8/8 rc=0。

---
---

**编译结束**: 2026-10-09 09:32
**最终状态**: published
