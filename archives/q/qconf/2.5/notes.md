# qconf 2.5 适配笔记

## 软件身份

- **软件名**: qconf 2.5 = QConf（qmake 工程的 configure 脚本生成器）
- **上游仓库**: https://github.com/psi-im/qconf （tag `v2.5` = `a06a3ca`；曾用名 `psi-plus/qconf`）
- **类型**: Qt5 控制台工具（`TEMPLATE=app`，`QT -= gui` + `QT += xml` + `CONFIG += console`），非库
- **状态**: `built`（conan create + conan-verify 全绿 + test_package 6/6 + 上游样例 4/4；
  `finish` 的 W3 门禁被**仓库级** JC 杂项（其他软件已跟踪的运行时状态文件）阻断，详见末节）

## 编译环境

- 构建系统: qmake（`qconf.pro`，in-source build；仓库内无 CMake/autotools）
- 编译日期: 2026-10-01
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，qmake `-spec linux-clang`）
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / clang 15 / libc++ / cppstd17 / Release）
- 并发: `make -j1`（本环境 `-j>1` 报 jobserver mkfifo 错误）

## 语言预检处置记录（R47）

`lang-preflight qconf 2.5 --src <src>` → `detected_language=mixed`，exit 2（自动写 env_unsupported）。
按 R47 附录 D.4「C/C++ 混编按主体判，不算 mixed」复核后**判 cpp 并继续主流程**（工具误判）：

- 源码构成：`cpp` 4（`src/qconf.cpp`、`src/stringhelp.cpp`、`conf/conf4.cpp`、`conf/conf.cpp`）、
  `c` 2（`src/configexe/configexe.c`、`embed.c`，Windows 专用 stub）、`bash` 1（`package.sh`，辅助脚本不计主体）
- 主体 = C++（`qconf.pro` / `src/qconf.cpp`）；`c + cpp` 合并占比 **6/6 = 100% ≥ 70%**
- 工具缺陷：`lang_detect._source_stats` 未合并 c/cpp（`max(4,2)/6 = 67% < 70%`），且
  `_manifest_scan` 不识别 qmake（纯 `.pro` 仓库无构建 manifest 兜底）→ 误落 `mixed`
- 处置：不采信 false-negative 终态，记录证据后继续；草稿见
  `knowledge/drafts/DRAFT-qconf-2.5-langpreflight-c-cpp-share-misdetect.{kv,md}`

## 依赖（W0 依赖发布检查：全部 EXIT=0 可消费）

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5Core + Qt5Xml（`QT += xml`）+ qmake/moc/rcc/uic |
| zlib | 1.3.1 | 传递（qt5-qtbase `self.requires`） |
| dbus | 1.14.10 | 传递（qt5-qtbase `self.requires`） |
| expat | 2.8.2 | 传递（dbus `self.requires`） |

**不依赖** `libX11`/`libXext`：v2.5 默认 `conf.qt4 = true` 走 `conf/conf4.*`（Qt5，无 gui/x11）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qmake 报 `Cannot read <stale>/mkspecs/modules-inst/qt_lib_core.pri` 且 `Project ERROR: Unknown module(s) in QT: core xml` | qt5-qtbase 包内 `mkspecs/modules/*.pri` 记录**构建期**绝对路径（`QT_MODULE_*_BASE`、`QT_TOOL.*.binary`、`include(<builddir>/mkspecs/modules-inst/...)`） | `_setup_qmake_modules()`：复制 `modules/*.pri` 到 build 目录并按正则 `/[^\s"'()]*?/p/b/[^/\s"'()]+/[bp]` 把构建期 conan 私有前缀改写为真实 package 目录，经 `QMAKEMODULES` 暴露 |
| 2 | 仅改写模块 .pri 仍报 `make: *** No rule to make target '../../qt5-<hash>/b/bin/rcc'` 与 rcc `inaccessible or not found` | `bin/qt.conf` 的 `[Paths] Prefix` 也是构建期路径 → `QT_INSTALL_BINS`/`LIBS` 解析到已消失目录（rcc/moc/uic 与产物 RUNPATH 同源） | 生成指向真实 package 的 `qt.conf` 并用 `qmake -qtconf` 加载（**不能带 `[EffectivePaths] Prefix=..`**，否则找不到 mkspec）；另用命令行 `QMAKE_RCC/QMAKE_MOC/QMAKE_UIC` 显式钉到 package `bin/`（命令行赋值优先级最高） |
| 3 | test_package 报 `qconf: cannot read <pkg>/bin/conf/conf4.h` | `copy(self, "conf/*", dst=<pkg>/bin/conf)` 会保留匹配到的相对路径 → 落到 `bin/conf/conf/` | `dst=<pkg>/bin`（保留 `conf/`、`modules/` 相对路径） |
| 4 | `make -j>1` 报 `jobserver mkfifo ... Operation not permitted` | 本机文件系统不允许创建 fifo | 用 `-j1`（qconf 仅 3 个 TU） |
| 5 | 产物 RPATH 曾指向构建期路径 | 同 #2（`QT_INSTALL_LIBS`） | `-qtconf` 修复后 RUNPATH = `<pkg>/lib`（已验证 `readelf -d`） |

## 上游测试情况（R51 三步法）

1. **清点**：上游**无自动化测试套件**——无 `tests/` 目录、无 `make check`/CTest/pytest 注册；
   可执行验证入口 = `examples/*.qc`（4 个样例）+ 仓库自带 `configure` 产物。
2. **实际运行**（用归档布局二进制实测，日志 `…/tmp/qconf-evidence/upstream_*.log`）：

   | 用例 | 命令 | 退出码 | 结果 |
   |------|------|--------|------|
   | `examples/sample.qc` | `qconf examples/sample.qc` | 0 | PASS（configure 41922 B） |
   | `examples/samplecustom.qc` | `qconf examples/samplecustom.qc` | 0 | PASS（41559 B） |
   | `examples/sampledeps.qc` | `qconf examples/sampledeps.qc` | 0 | PASS（42503 B，Deps: qt41*） |
   | `examples/samplelib.qc` | `qconf examples/samplelib.qc` | 0 | PASS（42074 B） |

   另 `qconf --version` → `qconf version: 2.0 by Psi IM Team`（EXIT=0）；`qconf --help` → 用法（EXIT=0）。
3. **统计**：**total=4 passed=4 failed=0 skipped=0**（通过率 100%，无漏测）。
   **鸿蒙特有测试用例 ≥1**：test_package `TC-06-ohos-aarch64-elf-runs-on-device`。

> test_package 不能替代上游测试统计，故上游 4 样例单独执行并单列。

## 验证结果

```bash
$ ohc-run.py conan-verify qconf 2.5            # EXIT=0
  Verdict: PASS   G0/G1/G2/G3/G4 PASS   L2/L4/L5 PASS
  （G2 = conan create 成功；日志 reports/conan-create.log）

$ grep CASE SUMMARY reports/conan-create.log
  CASE SUMMARY: total=6 passed=6 failed=0 skipped=0
  RESULT: PASS

$ file <pkg>/bin/qconf
  ELF 64-bit LSB arm64, dynamic, interpreter /lib/ld-musl-aarch64.so.1
$ readelf -d <pkg>/bin/qconf | grep -i runpath
  RUNPATH: [<qt5-qtbase pkg>/lib]
```

打包产物（`<conan cache>/p/…/p`）：

```
bin/qconf                     # 主程序（未 strip）
bin/conf/{conf.cpp,conf.pro,conf4.cpp,conf4.h,conf4.pro}
bin/modules/qt41.qcm          # 运行期数据（就地检测 applicationDirPath()/conf + /modules）
licenses/COPYING
```

## 已知阻断（如实记录，非本包缺陷）

`finish qconf 2.5 built` → **W3 HANDOFF**（`EXIT_REASON=w3_local_ci_failed` / `STEP_FAILED=Step5`），
唯一失败项为**仓库级 JC 杂项门禁**，命中文件**全部属于其他软件且已在 `main`**：

```
[FAIL] JC1: 5 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
       archives/k/kics/2.1.20/.staging-verified
       archives/l/libbfio/20260623/.staging-verified
       archives/t/thc/3.8/.staging-verified
[FAIL] JC5: 5 个 archives 下未登记的隐藏文件（同上，白名单 JC5_ALLOWED 未登记）
```
- 上述 5 个文件经 `git cat-file -e main:<path>` 确认**存在于 main**；`git ls-files archives/q/qconf | grep -E '/\.[^/]+$'` → **qconf 无已跟踪隐藏文件**
- qconf 自身的 `.build-closed` / `.handoff.json` 均被 `.gitignore` 忽略（第 270/277 行），不会进入 PR
- W3 的其余门禁全部通过：L0i（依赖在制品仓）/ L0j / L0k / L0l / L0m、KC、以及 `conan create` 本体（L1 起被 JC 阻断）
- Step 3 G0 干净构建验证为非阻塞项，其失败源于 `init-build` 把仓库自带 **生成的 `configure`** 误判为 autotools 入口
  （qconf 真实构建系统是 qmake），不影响 conan 流程

## 依赖版本

qt5-qtbase/5.15.2.2（→ zlib/1.3.1、dbus/1.14.10 → expat/2.8.2）

## 注意事项

- 上游 `src/qconf.cpp` 的 `#define VERSION "2.0"` 未随 tag 更新，故 `--version` 输出 `2.0`（上游行为，未改）
- qconf 生成 configure 后需下游自行执行 `./configure && make`；该步骤要求 `qmake` 在 PATH（下游使用场景）
---

**编译结束**: 2026-10-01 15:06
**最终状态**: built
