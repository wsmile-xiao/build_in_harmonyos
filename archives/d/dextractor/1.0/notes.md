# dextractor 1.0 适配笔记

## 概述

DEXTRACTOR（Gene Myers，https://github.com/thegenemyers/DEXTRACTOR，tag V1.0）是 PacBio 测序数据的压缩/解压命令行工具集，提供 5 个可执行文件：

| 工具 | 功能 | 依赖 |
|------|------|------|
| `dextract` | 从 `.bax.h5`（HDF5）提取 subread 与 QV 数据 | HDF5（含 zlib deflate 滤镜） |
| `dexta` / `undexta` | `.fasta` ↔ 2-bit `.dexta` 压缩 | 仅 libc |
| `dexqv` / `undexqv` | `.quiva` ↔ Huffman 压缩 `.dexqv` | 仅 libc |

语言：C（C99，无 C++ 特性）。构建系统：Makefile。

## 上游测试清点申报表（R51）

- 上游源码树 **无测试目录**：V1.0 共 11 个文件（Makefile、README、DB.c/h、QV.c/h、dextract.c、dexta.c、undexta.c、dexqv.c、undexqv.c），无 tests/、test/ 目录，无任何 `*_test` 文件。
- 上游 Makefile **无测试目标**：仅 `all` / `clean` / `install` / `package` 四个目标，无 check/test/ctest 入口。
- 结论：**上游测试用例数 = 0**，不存在可运行的上游测试套件。
- 适配后补全测试见 test_package/MANIFEST.yml 与 test.sh（消费者视角，实际执行构建产物）。

## 编译环境

- 构建系统: makefile（上游 Makefile）
- 编译日期: 2026-09-10（提交日；OHOS CI W3 待远端执行）
- 编译器: clang（Conan conf `tools.build:compiler_executables:c`，R33）
- 状态: partial（macOS 开发宿主机完成源码级验证；OHOS 真机构建由远程 CI 完成）

## 编译步骤（OHOS/Conan 视角）

```
make CC=<conan-clang> PATH_HDF5=<hdf5 依赖包 folder> -j1
```

- 上游 Makefile 规则体写死字面 `gcc`，`make CC=...` 无法覆盖 → 打补丁改为 `$(CC)`。
- `PATH_HDF5` 被 `-I$(PATH_HDF5)/include -L$(PATH_HDF5)/lib` 使用，直接指向 Conan 的 `hdf5/1.14.6` 包目录（含 include/ 与 lib/），无需再展开 cpp_info。
- 仅 `dextract` 链接 `-lhdf5`（动态库，Conan 管理依赖链）；其余 4 个工具无第三方依赖。
- 依赖链（均在制品仓已发布，PF4 探测确认）：`hdf5/1.14.6` → `libaec/1.1.7` + `zlib/1.3.1.1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 规则体写死 `gcc`，`make CC=` 覆盖无效 | 上游直接用字面编译器，未用 `$(CC)` 变量 | 补丁 0001：规则体改为 `$(CC)`，新增 `CC = gcc` 默认值保持上游行为 |
| 2 | `install:` 目标写死 `cp ... ~/bin` | 上游面向个人用户 | 补丁 0001：改为 `cp ... $(DEST_DIR)`，`DEST_DIR = $(HOME)/bin` 默认 |
| 3 | `PATH_HDF5` 硬编码 `/sw/apps/hdf5/current`、`/usr/local/hdf5` 两处 | 上游本地开发路径 | 补丁 0001：保留单默认值，make 命令行覆盖指向 Conan 依赖包 folder |
| 4 | 本机（macOS）无 HDF5，`dextract` 无法本地构建 | 依赖 hdf5/1.14.6 | 4 个非 HDF5 工具在本机实测通过；dextract 由 OHOS CI 构建并运行时验证（H5Zfilter_avail 探针） |
| 5 | degenerate quiva 输入（QV 全等于 run char）导致 dexqv 段错误 | 上游 Huffman 直方图清空无保护 | 上游限制，测试数据保持值多样即可规避；不做源码修改（R6 最小改动） |

## 源码修改

补丁文件：`patches/0001-makefile-portable-toolchain-and-install.patch`（仅 Makefile，无平台宏，R8 合规）：

1. 删除 `/sw/apps/hdf5/current` 硬编码，保留单一路径 `PATH_HDF5 = /usr/local/hdf5`（可被命令行覆盖）。
2. 新增 `CC = gcc` 与 `DEST_DIR = $(HOME)/bin` 变量定义。
3. 5 条构建规则的字面 `gcc` 全部改为 `$(CC)`。
4. `install:` 目标 `cp ... ~/bin` 改为 `cp ... $(DEST_DIR)`。

## 依赖版本

- hdf5/1.14.6（制品仓已发布；传递依赖 libaec/1.1.7、zlib/1.3.1.1 均已发布）
- 无系统级构建依赖（无需 autotools/cmake；仅 make + clang）

## 验证结果

### macOS 开发宿主机（本机实测，2026-09-10）

- `make CC=clang dexta undexta dexqv undexqv` → 4 工具全部编译通过，0 警告（Apple clang 17，-O3 -Wall -Wextra -fno-strict-aliasing）。
- T1 fasta 往返：`dexta -k` + `undexta` → 与输入**字节级一致**（2 条 read，120/80bp）。
- T2 quiva 往返：`dexqv -k` + `undexqv` → 头行 + delQV/insQV/mergeQV/subQV 10 行**逐行一致**；delTag 2 行按上游 2-bit 设计重建为 'a'/'n'（全局 delChar），与代码推导完全吻合。
- T3 错误路径：无参 / 非法选项 / 缺文件 → 均 rc=1 且打印对应错误。
- 注：`dextract`（HDF5 工具）本机无 HDF5 不构建，由 OHOS CI 构建 + test.sh T4 运行时验证（H5Zfilter_avail 探针：libhdf5.so 动态加载 + zlib deflate 滤镜可用）。

### OHOS PC（远程 CI）

- CI #45167（conan-build-test 全流程）：conan create 构建 5 工具全部成功（含 dextract 链接 `-lhdf5`），test_package T1-T3 全部 PASS；T4 因测试脚本调用语法失败（`-l 10` 分离写法被上游 ARG_NON_NEGATIVE 宏判为非整数，改为 `-l10` 后修复，见下）。
- CI 修复历程（#45116/#45120/#45123/#45167/#45178/#45182/#45186）：
  1. 版本 `1` → Conan 2.9 "Invalid package version"（须 X.Y），分支随之 `feat/dextractor-1` → `feat/dextractor-1.0`（L0n 要求分支=包名-版本精确匹配）。
  2. 补丁 strip：conandata 补丁默认 strip=0，补丁头带 `dextractor-1.0.orig/` 前缀须 `strip: 1`。
  3. `rindex` 链接失败：OHOS libc 裁剪 BSD 遗留符号 → 新增补丁 0002 将 DB.c 中 4 处 `rindex(` 替换为 POSIX `strrchr(`（对应知识草稿 DRAFT-cconv-0.6.3-rindex-strrchr；`index` 符号 OHOS 保留，无需处理）。
  4. T4 失败系测试脚本语法错误：上游 ARG_NON_NEGATIVE 要求选项值紧贴（`-l10`），`-l 10` 会提前打印 "argument is not an integer"；修正后 H5Zfilter_avail 探针可走到 Usage 分支。
- #45178/#45182/#45186：git-clone 步骤集群级基础设施故障（worker git 缺 libz.so，另一 PR #9732 同时段同失败），与包无关，等待恢复后重试。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 型配方（application），R33 编译器取自 Conan conf |
| conandata.yml | 官方源 V1.0 + SHA256 + 补丁声明 |
| patches/0001-makefile-portable-toolchain-and-install.patch | Makefile 可移植化（strip: 1） |
| patches/0002-db-c-rindex-to-strrchr.patch | DB.c `rindex(` → `strrchr(`（OHOS libc 裁剪，strip: 1） |
| test_package/ | conanfile.py + test.sh（15 断言）+ MANIFEST.yml |
| manifest.yaml | 版本级元数据（status: partial，待 CI） |
| ../manifest.yaml / README.md / commands.json | 软件级元数据与命令清单 |

## 注意事项

- **版本号**：上游 tag 为 `V1.0`（Debian 亦打包为 1.0），配方版本取 `1.0`；分支名 `feat/dextractor-1.0` 与 L0n 门禁一致（CI 实测：Conan 2.9 拒绝单段版本 `1`——"Invalid package version"，且 L0n 要求分支=包名-版本精确匹配；与用户 delay 任务同构，最终同样采用 `<库>-1.0` 分支）。
- **quiva delTag 有损**：按上游设计，delTag 流以 2-bit 编码（非 ACGT 字符 → 'a'，run 位 → 'n'），属格式语义，非适配引入。
- **degenerate 输入段错误**：QV 流全部等于 run char 时上游 Huffman 构建段错误（macOS 实测），属上游限制。
- **README 许可证**：上游无独立 LICENSE 文件，许可证文本（BSD-3-Clause 风格）在每个源文件头部；package() 将 README 放入 licenses/。
- **libXext/libxext 大小写路径**：仓库最新 main 同时含 `archives/l/libXext` 与 `archives/l/libxext`，在 macOS 大小写不敏感文件系统上检出会互相覆盖导致工作树显示脏状态——为上游既有现象，本分支提交不含这些文件。
