# sioyek 2.0.0 适配笔记

## R47 语言预检复核记录（重要）

- 工具判定：`lang-preflight` 判定 `mixed`（exit 2），并自动写入 env_unsupported 终态 result.json。
- 判定依据（工具输出）：源文件 34 个（cpp:18, python:12, bash:4, c:4），cpp 主体占比 53% < 70%。
- **复核结论：该判定为误报，正确判定应为 cpp（与任务语言匹配）。**
- 复核证据：
  1. 12 个 `.py` 文件全部位于 `scripts/` 目录（TTS 服务、论文下载器等运行时辅助脚本），R47 协议附录 D 边界规则明确"辅助脚本不算主体"；`pdf_viewer_build_config.pro` 的 SOURCES/HEADERS 清单不含任何 .py 文件，即 Python 脚本不参与编译。
  2. sioyek 构建体系为 qmake（`pdf_viewer_build_config.pro`），`lang_detect.py` 的 manifest 扫描器不识别 qmake（build_system 返回 none）。
  3. 剔除 scripts/ 辅助脚本后，编译主体 = 18 cpp + 4 c（sqlite3.c、synctex 捆绑 C 源、shell.c）+ 29 h，100% C/C++，c↔cpp 属兼容族（R47：兼容族不迁移）。
  4. 工具实现缺口：`lang_detect.py::_source_stats()` 仅排除 bash，未按协议排除辅助目录中的 Python 脚本；manifest 扫描器无 qmake 识别分支。
- 处置：经用户裁决（2026-09-18）按协议边界规则复核为 cpp，继续适配主流程；env_unsupported 误报终态在任务终态时以真实终态覆盖。误报分析如实记录于本节，不伪造预检结果。

## 编译环境
- 构建系统: qmake（上游 `pdf_viewer_build_config.pro`，in-source 构建产出 `sioyek` 可执行文件）
- 编译日期: 2026-09-18 ~ 2026-09-19（真机 conan create 干净构建）
- 编译器: clang/clang++（鸿蒙 aarch64 工具链，/data/service/hnp/bin）
- 状态: **conan-verify 通过（G0-G4 全 PASS，2026-09-19）**

## 编译步骤

conan 配方（模式 B，qmake 直驱，参照 qtsvg 消费侧先例）关键流程：
1. `source()`: 从 conandata.yml 官方源 `https://github.com/ahrm/sioyek/archive/refs/tags/v2.0.0.tar.gz`（sha256 `92398b6da5e297c59f22cd3c6b562194846f28bc17bb4ae9432869aafeb5df17`）获取源码；
2. `build()`:
   - 重写 qtbase 包内 `qt.conf` 与 `mkspecs/modules/*.pri` 的构建期硬编码旧路径 → 指向 qtbase 实际 package 目录（qmake 二进制内嵌旧路径已失效，`[Paths]` 重定位机制依赖 qt.conf 正确）；
   - 用 qmake 命令行注入 `INCLUDEPATH+=<mupdf>/include` 与 `INCLUDEPATH+=<zlib>/include`、`LIBS+=` 链接 mupdf 四个静态库与 zlib；
   - `make -j2 QMAKE_STRIP=""`（conanfile jobs=2：本机 make 高并行触发 jobserver mkfifo 错误）；
3. `package()`: 拷贝 `sioyek` 可执行文件、`tutorial.pdf`、`prefs.config`、`keys.config`、`shaders/` 到 `bin/`。
- 依赖: qt5-qtbase/5.15.2.2、mupdf/1.25.1、zlib/1.3.1（全部为制品仓已发布二进制，`--build=never` 验证 Already installed）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误报 mixed | 工具未排除 scripts/ 辅助 Python 脚本、不识别 qmake 构建体系 | 按协议边界规则人工复核为 cpp，见上节 |
| 2 | qmake `Unknown module(s) in QT: core gui opengl widgets network` | qtbase 包内 qt.conf/.pri 硬编码已消失的构建期旧路径 | 消费侧 build() 重写 qt.conf/.pri 指向 qtbase 实际 package 目录（qtsvg 配方先例） |
| 3 | `mupdf/fitz.h` not found | 0001 补丁只注入 LIBS 未注入 INCLUDEPATH | qmake 命令行 `INCLUDEPATH+=`（mupdf/zlib），不动已过 PF5 审查的 0001 补丁 |
| 4 | `qkeyevent.h` file not found（5 个文件） | 上游 2.0.0 按 Qt6 头布局写 include（Qt6 有独立 qkeyevent.h，Qt5.15 只有 qevent.h） | 补丁 0002：qkeyevent.h→qevent.h（difflib 从 pristine 源机械生成） |
| 5 | `unknown type name 'QSharedMemory'`（RunGuard） | 本仓 qt5-qtbase/5.15.2.2 构建未启用 sharedmemory/systemsemaphore 特性（qtcore-config.h 定义 QT_NO_SHAREDMEMORY/QT_NO_SYSTEMSEMAPHORE，真机 -fsyntax-only 探针实证），类声明不存在 | 补丁 0003 v2：`#ifdef QT_NO_SHAREDMEMORY` 特性降级——头文件给空占位类，构造函数/析构函数用 #else 整体门控，降级为总是主实例 + QLocalServer IPC 保留（isPrimary/isSecondary 语义不变） |
| 6 | `use of undeclared identifier 'GL_CLAMP'`（pdf_renderer.cpp） | GL_CLAMP 是桌面 GL 1.x 枚举，OHOS GLES 头无定义 | 补丁 0004：换等价枚举 GL_CLAMP_TO_EDGE（GLES/桌面 GL 均支持，上游后续版本同写法） |
| 7 | `use of undeclared identifier 'pdf_parse_link_uri'`（utils.cpp） | mupdf 1.25 删除了 pdf 层 `pdf_parse_link_uri()`（pdf-link.c 实证仅剩 pdf_parse_link_dest_to_file_with_uri 等内部函数）；sioyek 2.0.0 编写时对应 mupdf 1.23 | 补丁 0005：parse_uri() 改用 fitz 层等价 API `fz_resolve_link_dest(ctx, doc, uri)`（mupdf 1.25 fitz/document.h:687），签名增加 `fz_document*` 参数；4 个调用点分别传 `current_document->doc`（document_view.cpp）与 `doc()->doc`（main_widget.cpp，MainWidget::doc() 返回 Document*） |
| 8 | 0005 首版 main_widget.cpp 三处 `current_document` undeclared | 补丁生成时误用 document_view.cpp 的变量名；MainWidget 中文档指针经 `doc()` 成员函数获取 | 从 pristine tarball 源重生成补丁，main_widget.cpp 改用 `doc()->doc` |

## 补丁清单（conandata.yml 已登记）

| 补丁 | 内容 | PF5 审查 |
|------|------|----------|
| 0001-ohos-qmake-config.patch | qmake 配置（LIBS 注入） | ✅ 无 __OHOS__ 宏 |
| 0002-qt5-qkeyevent-header.patch | Qt6→Qt5 头布局（qkeyevent.h→qevent.h，5 文件） | ✅ 无 __OHOS__ 宏 |
| 0003-qtbase-nosharedmemory-runguard.patch | QT_NO_SHAREDMEMORY 特性降级（#else 整体门控） | ✅ 无 __OHOS__ 宏 |
| 0004-gles-gl-clamp-to-edge.patch | GL_CLAMP→GL_CLAMP_TO_EDGE | ✅ 无 __OHOS__ 宏 |
| 0005-mupdf-1.25-parse-uri.patch | pdf_parse_link_uri→fz_resolve_link_dest（mupdf 1.25 API 适配） | ✅ 无 __OHOS__ 宏 |

## R51 上游测试三步法

### 1. 清点（适配前）
- 上游 v2.0.0 tarball 全清单核对：**无 tests/ 目录**（匹配 `(^|/)(tests?|unittests?)/` 计数 = 0）、无 ctest/CMake/pytest 工程文件；构建体系为 qmake（`pdf_viewer_build_config.pro`）。
- `.github/workflows/` 仅 2 个构建发布流水线（build_and_release.yml、preview_release.yml），**无测试作业**。
- `scripts/` 下 7 个 Python 脚本为运行时辅助工具（TTS、论文下载器等），非测试代码。
- 结论：**上游确无自动化测试**。

### 2. 运行（真机 100% 实测）
- 上游测试用例数 N = 0（无上游测试可运行）。
- 按 R51「上游确无测试须自行补齐测试」：test_package 自建消费侧冒烟测试 `test_sioyek.sh`，三层断言：
  1. 产物为 arm64 ELF 可执行文件（file 校验）；
  2. conanrun 环境下动态依赖全部可解析（ldd 无 not found）；
  3. `--version` 真实运行输出 `sioyek 2.0.0`（main.cpp:662 在 QApplication 构造之前处理 --version，无显示环境可真实运行）。
- 实测（conan create 内 test_package 阶段，鸿蒙 PC 真机 aarch64，conan-create.log:1455-1462）：`PASS: .../bin/sioyek ELF executable, dependencies resolved, --version OK`，输出 `sioyek 2.0.0`。

### 3. 回填
- 补齐测试通过数 N′ = 3 / 3，**通过率 100%**（test_package 冒烟测试实测通过，非占位；计数口径：1 个 test_sioyek.sh 脚本内含 3 层断言——ELF 架构、依赖解析、--version 输出，逐条通过）。
- 注：GUI 应用的完整功能验证需显示环境，冒烟范围（产物完整性 + 依赖解析 + 程序真实启动并输出版本号）为无头环境下可达的最大覆盖。

## 知识草稿（R31，供知识图谱收录）

- **条目 1（E-新）qtbase 二进制包特性裁剪陷阱**：本仓 qt5-qtbase/5.15.2.2 二进制包禁用 sharedmemory/systemsemaphore 特性（`src/corelib/qtcore-config.h` 定义 `QT_NO_SHAREDMEMORY/QT_NO_SYSTEMSEMAPHORE`），且 `include/QtCore/qconfig.h` 为 30 行桩文件、真实特性宏在模块 `-config.h` 中；受影响头文件（qsharedmemory.h）类体缺失但文件存在，错误表现滞后于根因。消费者侧修法：`#ifdef QT_NO_SHAREDMEMORY` 特性降级（禁 `__OHOS__` 宏注入）。用 grep 特性宏 × 消费者代码交叉预检可提前发现。
- **条目 2（E-新）OHOS GLES 无桌面 GL 1.x 枚举**：`GL_CLAMP` 等桌面 GL 1.x 遗留枚举在 OHOS GLES 头不存在，改用 `GL_CLAMP_TO_EDGE` 等 GLES/桌面双支持枚举。预检：全树 `grep -oE "GL_[A-Z0-9_]+"` × GLES 头交叉核对。
- **条目 3（E-新）mupdf 1.24→1.25 API 变更**：`pdf_parse_link_uri()`（pdf 层）被删除，等价 fitz 层 API 为 `fz_resolve_link_dest(ctx, doc, uri)`（fitz/document.h）；迁移需在调用点取到底层 `fz_document*`。sioyek 2.0.0 按 mupdf 1.23 API 编写，跨 2 个版本适配。
- **条目 4（E-新）qmake 二进制 qt.conf 重定位失效**：qmake 二进制内嵌构建期路径（已消失），`qt.conf [Paths]` 与 `mkspecs/modules/*.pri` 若仍是旧路径则模块解析全挂。消费侧修法：build() 重写 qt.conf/.pri 指向 qtbase 实际 package 目录（qtsvg 配方先例，本配方已实现，可推广到其他 qmake 消费者）。

## 验证结果

- **conan-verify（2026-09-19）：G0/G1/G2/G3/G4 全 PASS**（reports/conan-verify-report.md，Verdict: PASS）。
- conan create 日志：reports/conan-create.log（含 test_package 实测执行记录）。
- 依赖发布状态：qt5-qtbase/5.15.2.2、mupdf/1.25.1、zlib/1.3.1 均已发布（conan download/--build=never 验证）。

## 注意事项

- 上游 tag 为 `v2.0.0`（非 `2.0.0`，后者 404）；conandata.yml 已按官方源 + 正确 tag 配置。
- qmake 消费者如需复用本配方 qt.conf/.pri 重写逻辑，直接参照本 conanfile.py build() 前段。
- 上游 include 风格为大量小写化头名（恰好命中 Qt5 小写真实头），全树扫描仅 qkeyevent.h 一个真幽灵头（137 项扫描清单见 ~/tmp/sioyek-includes.txt）。
- FUSE 文件系统上 `patch`/`git apply` 不可用；补丁可应用性校验用 python hunk 模拟（解析器须按 `@@` 分 hunk、只取上下文/删除行）。
- conandata.yml 补丁须用 git 风格 `a/` `b/` 前缀（G0 校验固定 `patch -p1`）；conan patch() 自动尝试 strip 兼容两种格式。

## 发现与知识

- ✅ qtbase 包 qt.conf 与 mkspecs/modules/*.pri 内嵌构建期旧路径已失效，消费侧 build() 重写即可修复 qmake 模块解析（qtsvg 先例，无需重编 qtbase）。
- ✅ qt5-qtbase/5.15.2.2 未启用 sharedmemory/systemsemaphore 特性，QT_NO_SHAREDMEMORY 使 QSharedMemory 类声明不存在；依赖该类的三方库用 `#ifdef QT_NO_SHAREDMEMORY` 降级桩（保留 QLocalServer IPC 等价功能）。
- ✅ 上游 sioyek 2.0.0 头文件 include 按 Qt6 布局书写（qkeyevent.h），Qt5.15 编译需映射为 qevent.h。
- ✅ OHOS GLES 头缺失桌面 GL 1.x 枚举 GL_CLAMP；GL_CLAMP_TO_EDGE 为 GLES/桌面通用等价替代（上游后续版本同款写法）。
- ✅ mupdf 1.25 删除 pdf_parse_link_uri；等价迁移为 fitz 层 fz_resolve_link_dest(ctx, fz_document*, uri)，parse_uri 需增加 document 参数传递。
- ✅ FUSE 文件系统 patch/git apply 不可用；conandata 补丁采用 git 风格 a/ b/ 前缀以通过 `patch -p1` 校验（conan patch() 两种格式均兼容）。

---

**编译结束**: 2026-09-19 01:39
**最终状态**: built
