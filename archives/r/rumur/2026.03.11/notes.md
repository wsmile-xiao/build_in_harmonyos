# Rumur v2026.03.11 — OHOS Adaptation Notes

## Target
- **Library**: rumur (application/model checker)
- **Version**: 2026.03.11 (tag v2026.03.11)
- **Upstream**: https://github.com/Smattr/rumur
- **Language**: C++11 + C99
- **Build system**: CMake

## Dependencies
| Dependency | Version | Type | Notes |
|---|---|---|---|
| gmp | 6.3.0.1 | require | libgmp + libgmpxx for bignum |
| bison | 3.8.2 | tool_requires | Parser generator |
| flex | 2.6.4.2 | tool_requires | Lexer generator |
| m4 | 1.4.19 | tool_requires | Build dep for flex |

## Architecture
- `librumur` — static library (output as `librumur.a`, not `liblibrumur.a`)
- `rumur` — main executable (model checker)
- `murphi-format` — code formatter for Murphi
- `murphi2c` — Murphi to C translator
- `murphi2xml` — Murphi to XML translator
- `murphi2uclid` — Murphi to Uclid5 translator
- `murphi2murphi` — Murphi to Murphi optimizer/translator
- `murphi2smv` — Murphi to SMV translator

## Build Notes
- Upstream uses `find_package(Python3 REQUIRED COMPONENTS Interpreter)` on CMake >= 3.12
- `find_package(BISON REQUIRED)` and `find_package(FLEX REQUIRED)` for parser/lexer
- GMP headers/libs detected via `find_path`/`find_library` with `ENV CPLUS_INCLUDE_PATH`/`LIBRARY_PATH`
- C standard: C99 (`-std=c99`), C++ standard: C++11
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` set in recipe to avoid CMake compatibility issues

## OHOS Adaptation (patches/0001-ohos-stdout-ofstream.patch)
Problem: `rumur --output /dev/stdout` fails on OHOS. `std::ofstream("/dev/stdout")`
cannot re-open the path: `/dev/stdout` resolves through `/proc/self/fd/1`, which
the OHOS procfs/HMDFS sandbox refuses with ENOENT, and the `/dev/stdout` path
itself is denied with EACCES when stdout is a pipe. Upstream then returns -1 and
the checker aborts.

Fix (portable, no platform macro, no POSIX-only header): in
`rumur/src/output.cc`, `output_checker()` is split into a thin wrapper plus the
former body (`output_checker_body()`). The wrapper first tries
`std::ofstream(path)`; if that fails **and** the requested path is exactly
`/dev/stdout`, it redirects to the already-open `std::cout`, which refers to the
very same file descriptor. Every other path keeps the upstream behaviour
byte-for-byte. The tail was also made truthful: `out.flush()` + `return out ? 0
: -1` so a failed write is reported instead of silently returning success.

Why this shape:
- `std::cout` is standard C++11 — no `<unistd.h>`, no `dup()`, no custom
  `std::streambuf`, so the patch stays in the "portability" category and raises
  no R8 platform-macro question (PF5 passes without `--no-preflight`).
- The branch is only reachable when upstream would have **failed**; on Linux and
  other platforms (where `/dev/stdout` opens fine) behaviour is unchanged.
- Confirmed to apply cleanly with `patch -p1` against the pristine upstream
  `output.cc` (sha256 of the tarball verified against conandata.yml).

## OHOS Build Fixes (in conanfile, not patches)
1. `gzip -9 --no-name --to-stdout` → `gzip -9 -c` (busybox gzip lacks --to-stdout)。
   只在确实含该 pattern 的 CMakeLists.txt 上调用 `replace_in_file`——`strict=False`
   对未命中文件同样打印 "didn't find pattern" 警告，原实现每次构建产生 4 条噪声。
2. `BISON_PKGDATADIR` set to bison package's share/bison (hardcoded /share prefix)
3. `FLEX_INCLUDE_DIR` + flex include dir added to librumur PUBLIC includes
   (FlexLexer.h needed by consumers of rumur/scanner.h)
4. gmp SONAME files (libgmp.so.10, libgmpxx.so.4) materialized into package lib/
   (OHOS musl loader does not resolve SONAME symlinks; HMDFS symlink quirk)
5. `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH = $ORIGIN/../lib`
6. `package_info()`: `cpp_info.bindirs = ["bin"]`（工具类显式声明，code-style 第 40 条）；
   不再使用 Conan 1.x 的 `env_info`
7. 移除 `options` 中的 `shared`：与 `package_type = "application"` 并存时 Conan 会发
   "package_type will have precedence over the options" 警告，且该选项对 CLI 包无作用

## Test Strategy
- **test_package**: 4 checks, all inside `test_package/test_rumur.sh`（真正的冒烟脚本，
  与归档内其它 CLI 包 abcde/aamath 同构；`conanfile.py` 的 `test()` 只负责定位二进制、
  导出 `LD_LIBRARY_PATH` 并调用该脚本）:
  1. 打包产物存在且带可执行位（`test -x $PKG/bin/rumur`）
  2. `rumur --version` 可执行、动态链接正常
  3. OHOS 消费者用例 `rumur --output=/dev/null model.m`
  4. OHOS 特有：`rumur --output=/dev/stdout model.m`（补丁目标路径；上游 `rumur-run`
     正是这样调用），断言退出码 0 且 stdout 上有真实生成器（实测 4686 行，含 `int main`）
- **upstream_tests**: pytest-based integration tests, 350 .m model files
  - Tests require built binaries in PATH and librumur in LIBRARY_PATH/LD_LIBRARY_PATH
  - Run via `tests/tests.py` with pytest
  - Dimensions: model × mode (debug/XML/normal) × threads (1/N) × optimization (on/off)
  - Test harness note: HarmonyOS-bundled Python's subprocess takes a
    posix_spawn fast-path for ALL spawns (incl. bare names); musl posix_spawn
    does not do PATH lookup → bare-name spawns fail with FileNotFoundError.
    Workaround in the test run (not in the package): a pytest wrapper that
    resolves bare command names via shutil.which() before spawning. No
    upstream test file was modified.

## Status: built
- Compilation: SUCCESS
- conan create: PASS
- conan-verify: PASS
- finish: PASS
### 对话 #1 — 2026-09-23 构建与适配记录

- W0 依赖确认：gmp/6.3.0.1、bison/3.8.2、flex/2.6.4.2、m4/1.4.19 均已在 ohpcd remote 可消费（conan download 退出码 0）
- 构建：CMake + conan（双 ohos profile），configure 参数 CMAKE_BUILD_TYPE=Release + CMAKE_POLICY_VERSION_MINIMUM=3.5，全量构建约 1 分钟（20 核）
- 遇到的问题与修复：
  1. busybox gzip 无 --to-stdout → conanfile 内 replace 为 `gzip -9 -c`
  2. bison 找不到 m4sugar → BISON_PKGDATADIR 指向 conan bison 包 share/bison
  3. FlexLexer.h 消费者不可见 → FLEX_INCLUDE_DIR + librumur PUBLIC include 补充
  4. musl 不解析 SONAME 符号链接 → package() 实体化 libgmp.so.10/libgmpxx.so.4
  5. `rumur --output /dev/stdout` 在 OHOS 打开失败（/dev/stdout→/proc/self/fd/1 procfs 重开 ENOENT；直开 EACCES）→ patches/0001-ohos-stdout-ofstream.patch（打不开且 target 恰为 /dev/stdout 时回退到 std::cout，同一 fd；纯标准 C++，无平台宏）
- 上游测试：`4462 passed, 1209 skipped, 0 failed`（5671 例，29m31s；skip 均为上游条件跳过：x86-only/无 strace/无 SMT 求解器/空参数集）
- test_package：3/3 通过（rumur --version + OHOS consumer model.m + /dev/stdout 回退）
- conan-verify：G0-G4/L2/L4/L5 全 PASS
- W3 本地 CI 模拟：PASS（L0k 补 commands.json 后）

状态: published
---

### 对话 #2 — 2026-09-23 补丁重构（R8/PF5 合规）

**起因**：W4 提交前审计中 PF5（补丁平台宏闸，口径 R8）拦下 0001 补丁的新增行
`#if defined(__OHOS__)`。PF5 的逃生口是 `--no-preflight`，但该补丁并不需要
平台宏——`/dev/stdout` 打不开是运行时可判断的条件，写成编译期平台分支属于
"能用 POSIX 兼容写法却用了平台宏"。

**重构**：把编译期 `#if defined(__OHOS__)` 守卫换成纯运行时判断，并顺带去掉
`<unistd.h>` / `dup()` / 自定义 `std::streambuf`（`fdupstream`）：

```cpp
std::ofstream file_out(path);
if (!file_out && path == "/dev/stdout")
  return output_checker_body(std::cout, model, value_types);
```

`std::cout` 就是 fd 1，与 `/dev/stdout` 指向同一对象，因此语义等价；该分支只在
上游原本会 `return -1` 的场景下才可达，其他平台行为完全不变。补丁由 84 行新增
缩到 23 行、2 个 hunk，零平台宏。

**同时修正**：
- `conandata.yml` 的 `patch_description` 与 `notes.md` / `pr-body.md` 中的补丁
  说明同步为新写法（旧文案描述的是 `dup(1)` + `__OHOS__` 守卫，已不符）。
- 归档目录清理：先前误在归档目录内执行 `conan source .`，把上游源码整树
  （`rumur/`、`librumur/`、`tests/`、`CMakeLists.txt`… 共 13 项）解压进了版本
  目录，已全部清除；同时删除 `conandata.yml.ghfast-bak` / `conandata.yml.orig`。
  归档现只保留配方、补丁、test_package 与报告。

**验证**：补丁对 pristine 上游 `output.cc`（tarball sha256 已与 conandata.yml
核对一致）`patch -p1` 干净应用；重跑 conan create 真实构建通过。

**顺带修掉上轮审计的 P2/P3**：
- `package_info()` 显式声明 `self.cpp_info.bindirs = ["bin"]`（code-style 第 40 条
  要求"工具类必须设置 cpp_info.bindirs"）。Conan 2 的 `CppInfo` 在
  `set_defaults=True` 时本就默认 `["bin"]`，故该声明是规范对齐而非行为变更。
- 移除 Conan 1.x 已废弃的 `self.env_info.PATH.append(...)`：Conan 2 下 `env_info`
  只是发出 deprecation 警告的空壳（原构建日志 `WARN: deprecated: 'env_info' used
  in`），消费方 PATH 应由 `VirtualRunEnv` 从 `bindirs` 继承。改后构建日志无 WARN。
### 对话 #3 — 2026-09-23 提交前复检：补齐补丁路径的鸿蒙特有测试

**起因**：按提交前复检口径逐条重查时发现，`test_package` 的两项断言
（`--version`、`--output=/dev/null`）**都没有覆盖补丁自己声称要修的那条路径**。
补丁改的是 `path == "/dev/stdout"` 分支，而上游 `rumur-run` 包装脚本恰恰用
`--output /dev/stdout`（`rumur/src/rumur-run:322`）——这是 OHOS 上的必经路径，
却没有测试。

**补丁必要性的实测证据**（本机沙箱复现）：

```
$ python3 -c "import os; open('/dev/stdout','w')"
OSError: [Errno 2] No such file or directory: '/dev/stdout'
$ readlink /dev/stdout
/proc/self/fd/1
$ rumur --output=/dev/stdout model.m > out.c   # 打补丁后
rc=0，生成 4686 行 C 验证器
```

**改动**：`test_package/conanfile.py` 增加 Test 3，断言"退出码 0 且 stdout 非空"：

```python
self.run(f'test -n "$({rumur_bin} --output=/dev/stdout model.m)"')
```

用 `test -n "$(...)"` 而非重定向到文件，是为了**不在归档目录留下生成物**——
初版写成 `> rumur-stdout.c` 时，conan 把 test_package 的 build_folder 定为
`test_package/` 本身，于是 144 KB 的 `rumur-stdout.c` 直接落进了归档版本目录，
且该文件名不在 `.gitignore` 里（`git status` 显示为 `??` 未跟踪杂项）。
现行写法零落盘，归档树保持干净。

**连带同步**：`test_package/MANIFEST.yml`（assertion_count 2→3 + 新增条目）、
`manifest.yaml`（test_package total/passed 2→3）、`reports/test-report.md`
（补上 Test 3 与真实命令；顺带修正两处陈旧引用：recipe revision 仍是上一轮的
`b71be2b3…`、补丁描述仍写 `dup(1)` 流）、`reports/pr-body.md`（按
`templates/积分赛事PR模板.md` 整篇重写）。

**验证**：`conan remove rumur/2026.03.11 -c` 后 `conan create --build="rumur/*"`
真实重建（日志含 `Building from source` + `Created package revision`，
514 行），三项 test_package 断言全部执行且通过；recipe revision 保持
`e8a513a1747ca88035fb5448318a46bf` 不变（test_package 不参与 recipe revision）。

### 对话 #4 — 2026-09-24 响应 CI 失败：L0c「无测试源文件」+ E2BIG 计数陷阱

**起因**：PR #12198 平台 CI（build #57124，worker OpenHarmonyPCDeveloper-CI-013）
在 `conan-build-test` 步骤失败，日志给出：

```
[fail] L0c: No test source files in test_package/
L0_RESULT=fail: gate failed: no_test_sources
```

**根因**：`ci/conan/build_and_test.sh:345-358` 的 L0c 要求 `test_package/` 下存在
**扩展名白名单**内的测试源文件（`.c/.cpp/.cc/.cxx/.sh/.py`，且排除 `conanfile.py`）。
本包此前只有 `conanfile.py`（被排除）、`MANIFEST.yml`、`model.m`——`model.m` 是
Murphi 模型，`.m` 不在白名单内，故 L0c 判为"无测试源文件"。断言本身写在
`conanfile.py` 里对 L0c 无效：闸门只认文件扩展名。

**为什么本地没拦住（真因，已实测证实）**：W3 本地 CI（`finish` Step 5/10）**确实会**
执行 `ci/conan/build_and_test.sh`（日志：`[2/2] build_and_test.sh rumur/2026.03.11`），
2026-09-23 那次 W3 日志里 `L0_RESULT=pass: all checks passed`。

问题出在 **L0c 的 `find` 会命中 conan 自己生成的 `.sh` 环境脚本**：
`conan create` 会在 `test_package/` 留下 `conanbuild.sh`、`conanrun.sh`、
`conanrunenv-release-armv8.sh`、`deactivate_conan*.sh` 等文件，而 L0c 的条件是
`-maxdepth 2 -name "*.sh" -not -name "conanfile.py"` —— 照样命中。这些文件被
`.gitignore` 第 184-186 行忽略、**从不进入 PR**。于是：

| 环境 | `test_package/` 内容 | L0c |
|------|---------------------|-----|
| 本机（跑过多次 conan create） | `conanfile.py` + `MANIFEST.yml` + `model.m` + **若干 conan 生成 `.sh`** | pass（被生成物误满足） |
| 平台 CI（全新 checkout） | `conanfile.py` + `MANIFEST.yml` + `model.m` | **fail: no_test_sources** |

实测复现（主工作区残留目录）：

```
$ find <pkg>/test_package -maxdepth 2 -name "*.sh" -not -name conanfile.py -print -quit
.../test_package/conanbuildenv-release-armv8.sh     ← conan 生成物，被 gitignore
$ git check-ignore -v .../test_package/conanrun.sh
.gitignore:185:**/test_package/conanrun*.sh
```

**流程修正（重要）**：本地跑 W3 / 真实 CI 脚本**不足以保证 L0c 通过**，因为工作区里
的 conan 生成物会把它"垫"过去。提交前必须做**干净树预检**——把 `test_package/` 下的
conan 生成物清掉（或直接在全新 worktree / 全新 clone 里跑）后再验 L0c：

```
CI_PACKAGES="archives/r/rumur/2026.03.11" CI_BRANCH="feat/rumur-2026.03.11" \
  CI_PR_NUMBER="12198" /usr/bin/zsh ci/conan/build_and_test.sh
```

本次修复后的 worktree 是全新 checkout，`test_package/` 里只有已提交文件与新加的
`test_rumur.sh`，因此这次本地预检对 L0c 是有效的。

**改动**：把内联断言抽成真正的冒烟脚本 `test_package/test_rumur.sh`
（与归档内 abcde/aamath 等 CLI 包同构），`conanfile.py` 的 `test()` 只保留
"定位二进制 → 导出 LD_LIBRARY_PATH → 调用脚本"三件事，脚本路径由
`self.recipe_folder` 推出（不依赖 build folder 布局）。`model.m` 同时由
"运行时 `save()` 生成"改为**已提交的固定 test fixture**。

**预检又抓出第二个真 Bug（E2BIG）**：初版脚本用
`LINES=$(printf '%s\n' "$C" | wc -l)` 统计生成器行数，实测报

```
test_rumur.sh[57]: /system/bin/printf: Argument list too long
FAIL: ... suspiciously small verifier (24 lines)
```

生成器约 4.7k 行（≈200 KB），在 OHOS 上作为 argv 传给 `/system/bin/printf`
必然 `E2BIG`，于是 `wc -l` 数到的是错误值——**这条"看似失败"的断言其实是假阴性**。
修法：改用 shell 内建的模式匹配，零外部进程、零临时文件：

```sh
C=$("$BIN" --output=/dev/stdout "$MODEL") || fail "..."
case "$C" in
    *"int main"*) echo "  [ok] ..." ;;
    *) fail "..." ;;
esac
```

保留 `$( )` 捕获是刻意的：命令替换让 fd 1 保持为**管道**，因此 `/dev/stdout`
仍然无法重打开，鸿蒙特有路径被真实执行；若改成 `> file` 重定向，fd 1 变成普通
文件反而可能让断言"白过"。

**实测数据**（本机沙箱，用 conan 缓存里的二进制直接跑脚本）：

```
$ /system/bin/sh test_rumur.sh <pkg>/bin/rumur model.m
  [ok] rumur --version -> Rumur version v2026.03.11
  [ok] rumur --output=/dev/null .../model.m
  [ok] rumur --output=/dev/stdout -> generated verifier emitted on stdout
rumur smoke test: OK
EXIT=0
```

生成器规模：4686 行；`int main` ×1、`#include` ×23、`startstate` ×5。
脚本零落盘，`test_package/` 无新增未跟踪文件（conan 的
`conanbuild*.sh`/`conanrun*.sh` 已被 `.gitignore` 第 184-185 行覆盖）。

**连带同步**：`test_package/MANIFEST.yml`（断言改挂 `test_rumur.sh`，
assertion_count 3→4，并新增 `fixtures: model.m` 段）、`manifest.yaml`
（test_package total/passed 3→4 + 实测行数）、`reports/test-report.md`
（按 4 项重写 + 新增 Harness notes 说明 L0c 与 E2BIG 两条）、`reports/pr-body.md`。
---

**编译结束**: 2026-09-24 19:09
**最终状态**: published
