# irstlm 6.00.05 知识候选台账（Knowledge Candidate Ledger）

任务：irstlm-6.00.05-r01-pc1-56（知识库扩展路径评估）
日期：2026-09-21

## 声明

irstlm 6.00.05 为 C++ autotools + GitHub tag 分发。适配过程实际遇到的错误全部为
可复现的构建/平台问题，逐项按"真实错误 → 根因 → 修复 → 验证 → 适用范围"登记，
并在四范围（正式 knowledge/graph/E*.kv、图谱 index.tsv、草稿 knowledge/drafts/、
人类文档 knowledge/doc/）完成七轴查重。

---

## 候选 C1：GitHub tag tarball 不含 autotools 生成文件，配方需 autoreconf 自举

- **真实错误**：`conan create` → `configure: inaccessible or not found`（exit 127），
  源码目录只有 configure.ac/Makefile.am，无 configure/config.guess/config.sub/install-sh。
- **根因**：上游只把 autotools *输入* 文件（configure.ac、Makefile.am）纳入 git，
  *生成* 文件（configure、config.guess、config.sub、Makefile.in、install-sh）由
  autoreconf/automake 在发布时生成，因此 `archive/refs/tags/*.tar.gz` 分发物
  天然不含这些文件。
- **修复**：配方 `build_requirements()` 增加 `tool_requires("automake/1.18")` +
  `tool_requires("libtool/2.5.4")`；`build()` 首先在 source_folder 执行
  `autoreconf -fi`（irstlm 自带 `regenerate-makefiles.sh` 等价逻辑），再
  `autotools.configure()`。
- **验证**：conan-verify G2 conan create 全绿（含 test_package 1/1）；W3 本地 CI
  L0/L1/L2/L4/L5 全 pass（Pass rate 100%）。
- **适用范围**：**所有以 GitHub tag tarball 分发的 autotools 项目**。
- **查重（四范围）**：
  - 正式条目：E175（config.status HMDFS 临时目录，方案同为 autoreconf-regenerate，
    **trigger 不同**——E175 针对 HMDFS 写入失败，C1 针对 tarball 缺生成文件）；
    E178（工具链缺 automake → autoreconf 失败，trigger_overlap）；均未直接覆盖
    “tarball 无生成文件须自举”这一触发面。
  - 图谱：index.tsv 无对应条目。
  - 草稿：DRAFT-5982-gmime（release tarball native-run-probe，trigger_overlap）；
    DRAFT-E569（codeload URL 302 直连，不相关）。
  - 文档：build-systems.md §autotools 提及 autoreconf 后修改丢失，未覆盖自举模式。

## 候选 C2：autotools configure.ac 把 `-std=c++0x` 注入 CPPFLAGS 导致 C 源编译失败

- **真实错误**：`clang: error: invalid argument '-std=c++0x' not allowed with 'C'`
  （cmd.c/thpool.c 编译，make[2] exit 2）。
- **根因**：上游 configure.ac 用 `CPPFLAGS="$CPPFLAGS -DHAVE_CXX0 -std=c++0x"`，
  CPPFLAGS 同时作用于 C/C++ 编译，C 编译器拒绝 C++ 专用 `-std=c++0x`。
- **修复**（补丁 0002）：把 `-std=c++0x` 从 CPPFLAGS 移到 CXXFLAGS
  （`CXXFLAGS="$CXXFLAGS -std=c++0x"`），CPPFLAGS 只保留 `-DHAVE_CXX0`。
- **验证**：补丁应用后 conan create 编译全绿；W3 门禁全过。
- **适用范围**：所有在 configure.ac/CPPFLAGS 注入 C++ 专用 -std= 标志的 autotools
  项目（C/C++ 混编库尤甚）。
- **查重（四范围）**：
  - 正式条目：无。E065（gnulib CPPFLAGS include 顺序）不相关。
  - 图谱/文档：index.tsv、doc/ 均无对应。
  - 草稿：DRAFT-ohos-cmake-normal-var-shadows-toolchain-standard
    （CMake 场景 `-std=c++20` 泄漏进 extra_cflags 报
    `invalid argument '-std=c++20' not allowed with 'C'`）——
    **trigger_overlap**（同为 -std= 泄漏到 C 编译），但构建系统（CMake vs
    autotools）、根因（普通变量遮蔽 cache vs CPPFLAGS 注入）、修复面
    （extra_cflags 取舍 vs CPPFLAGS→CXXFLAGS 拆分）均不同，属 **partial
    cover + 新增差异（autotools 特定修复形态，可跨 autotools 库复用）**。

## 候选 C3：install-exec-hook 在 prefix=/ 时创建 lib→lib64 软链失败

- **真实错误**：`ln: cannot create symbolic link from 'lib' to 'lib64': Permission
  denied`（make install-exec-hook，conan create package() 阶段 exit 2）。
- **根因**：Makefile.am `install-exec-hook` 在 `${exec_prefix}/` 下器 `ln -s lib
  lib64`；conan 安装 prefix=/，根目录无写权限。
- **修复**（补丁 0001）：删除该 install-exec-hook（历史 lib64 兼容遗留，对
  conan 静态库交付无意义）。
- **验证**：补丁应用后 make install 全绿；test_package 1/1。
- **适用范围**：带 lib→lib64 软链 install-exec-hook 的 autotools 项目。
- **查重（四范围）**：
  - 正式条目：E080（Python venv 的 lib64 symlink Permission denied）——
    **trigger_overlap**（同为 HMDFS/权限下 lib64 软链失败），但根因（Python 3.9
    venv 强制软链 vs autotools install hook）、修复（try/except vs 删除 hook）
    不同。
  - 图谱/草稿/文档：无对应。

## 候选 C4：HMDFS 上 `umask 077` 临时目录不可写（config.status subs1.awk 失败）

- **真实错误**：`can't create .../confXXXXXX/subs1.awk: Permission denied` →
  `config.status: error: could not setup config files machinery`。
- **根因**：E011/E114：HMDFS 把 umask 077 创建的 0700 目录变成 drwx--S--- 且
  不可写；configure 生成 config.status 时 `umask 077 && mktemp -d` 触发。
- **修复**：配方 build() 对生成的 configure 执行 `umask 077` → `umask 022`
  替换（_drop_umask_077 辅助函数，与 abiword-plugin-clarisworks 同款）。
- **验证**：替换后 configure/config.status 全绿。
- **适用范围**：所有在 HMDFS 上跑 autotools configure 的项目。
- **查重**：E011/E052/E060/E110/E112/E175 多条已覆盖，**exact_duplicate，
  复用既有条目，不建新草稿**。

## 候选 C5：make/ctest -jN 在 HMDFS 触发 jobserver fifo EPERM

- **真实错误**：`make: jobserver mkfifo: .../GMfifoXXXX: Operation not permitted`。
- **根因**：E074：HMDFS 不允许 fifo，make jobserver 无法建管。
- **修复**：make -j1 / ctest -j1（配方 build()、test_package 均已固化）。
- **验证**：-j1 后全链路通过。
- **查重**：E074 已覆盖，**exact_duplicate，复用，不建草稿**。

## 候选 C6：zlib 无条件依赖（configure.ac `LIBS="$LIBS -lz"`）

- **真实错误**：test_package 链接 `undefined symbol: gzopen/gzclose/gzread`。
- **根因**：mfstream.cpp/gzfilebuf.h 使用 zlib，configure.ac 无条件 -lz。
- **修复**：配方 `self.requires("zlib/1.3.1")`。
- **验证**：声明后链接全绿。
- **查重**：属常规依赖声明（R18/R35/R36 流程内动作），非独立知识；归档 manifest
  dependencies 记录即可，不建草稿。

## 候选 C7：config.guess 无法识别 HarmonyOS（E007 已知）

- **真实错误**：`cannot guess build type; you must specify one`。
- **根因**：E007：config.guess 无 HarmonyOS 检测分支；uname -s=HarmonyOS。
- **修复**：配方 generate() 显式
  `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  （config.sub 支持 *-linux-ohos，跳过 config.guess 探测；与 abiword-plugin-*
  同款）。
- **验证**：configure 全绿。
- **查重**：E007 已覆盖（触发面一致），修复路径为仓库既有实践，
  **exact_duplicate，复用，不建草稿**。

---

## 七轴查重汇总

| 候选 | exact_duplicate | causal_duplicate | trigger_overlap | solution_overlap | combination_novelty | boundary_novelty | test_migration_novelty |
|------|-----------------|------------------|-----------------|------------------|---------------------|------------------|------------------------|
| C1 tarball 无 configure 自举 | 否 | 否 | E175/E178 部分（autoreconf） | E175 部分（autoreconf-regenerate） | 是（tarball 分发形态 → 配方自举全链路） | 是（GitHub tag 分发 + tool_requires 自举组合未入库） | 否 |
| C2 cxx0 泄漏到 C 编译 | 否 | 否 | CMake 草稿（-std= 到 C） | 部分（不注入 extra_cflags 同理） | 是（autotools CPPFLAGS→CXXFLAGS 拆分） | 是（autotools 特定修复形态未入库） | 否 |
| C3 install hook lib64 软链 | 否 | 否 | E080（lib64 软链失败） | 否 | 是（删除 hook 处理） | 是 | 否 |
| C4 umask077 config.status | **是**（E011/E052/E060/E110/E112/E175） | 是 | 是 | 是 | 否 | 否 | 否 |
| C5 jobserver fifo | **是**（E074） | 是 | 是 | 是 | 否 | 否 | 否 |
| C6 zlib 依赖 | 常规流程 | — | — | — | 否 | 否 | 否 |
| C7 config.guess OHOS | **是**（E007） | 是 | 是 | 是 | 否 | 否 | 否 |

**关系字段**：
- C2 similar_to DRAFT-ohos-cmake-normal-var-shadows-toolchain-standard
- C3 similar_to E080；C1 prerequisite_of C4（autoreconf 生成 configure 后才遇到
  config.status umask 问题）；C7 caused_by（上游 config.guess 问题）→ 已 E007 覆盖
- C4/C5/C7 conflicts_with：无（既有条目完全覆盖）

## 路径决定

- **new_draft**：候选 C1 + C2 均已由本轮真实日志验证、可跨库复用、查重为
  partial/未命中且存在新增差异 → 走**路径 B（知识库扩展）**，为两个候选建立
  同 stem 的 .md/.kv 草稿对（DRAFT-C1/C2 见 knowledge/drafts/）。
- 复用（不建草稿）：C4（E011 系）、C5（E074）、C7（E007）。
- C6 属常规配方工作，随 manifest 归档记录。

确认：`reuse_existing` = C4/C5/C7；`new_draft` = C1、C2；`path_a_no_knowledge` = 否。