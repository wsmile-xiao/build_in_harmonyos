# pfstools 2.2.0 适配笔记

## 状态声明
- **非构建前置段（主理-11，A 机）**：源码取证 + 构建系统实证 + W0 依赖只读核验 + 语言面自证 + 配方初稿落盘。
- **构建段与门禁（主理-23，B 机 2026-09-24）**：conan create / conan-verify / W3 本地 CI 模拟 / finish 已真机执行，
  `status: built`，W3 通过（`.ci-result.json` exit_code=0，日志 `reports/w3-local-ci.log`）。
- 本文件下方「构建段实测」段的每条数字都有同目录日志佐证。

## 编译环境（实测）
- 构建系统: CMake（顶层 `cmake_minimum_required(VERSION 2.8.8)`；设备 cmake **4.1.2**）
- 目标: os=OHOS / os.version=6.0 / arch=armv8 / clang-15 / libc++ / cppstd=17（`ci/conan/profiles/ohos-aarch64`）
- 工具链实测: conan 2.29.1 / bash 5.3.9 / perl 5.42.0
- 状态: **built**（requirements 为空，全部可选依赖关闭）


## 源码取证
| 项 | 值 |
|---|---|
| URL | `https://sourceforge.net/projects/pfstools/files/pfstools/2.2.0/pfstools-2.2.0.tgz` |
| HTTP | 200（`downloads.sourceforge.net` 重定向；默认镜像 twds/versaweb/netix 等多次 curl 52/28 失败，phoenixnap/ufpr/jaist 三镜像取回一致） |
| 字节数 | 614772 |
| sha256 | `9bf6844985663226c21998eeb43c261acb8e4b3891b9a91b729554406289d7ca` |
| `file` | gzip compressed data |
| 条目数 | 394 |
| 顶层结构 | **单一根目录 `pfstools-2.2.0/`**，无 `./` 前缀条目（grep 计数 0），无多根 ⇒ `strip_root=True` **安全**（conan get 不会静默不剥根） |

## 构建系统实证（顶层 CMakeLists.txt，349 行）
- **cmake 最低版本**: `2.8.8`（第 1 行）
- **C++ 标准**: 上游**未显式设置**（全仓无 `CMAKE_CXX_STANDARD`/`CXX_STANDARD`/`-std=c++*`，唯一一处是 matlab 下被注释掉的 `-std=c++11`）⇒ 实际由 profile `compiler.cppstd=17`（CMakeToolchain 注入）决定
- **find_package 面**（14 项，含无开关的两项）:

| find_package | OPTION 开关（逐字） | 默认 | 关闭后缺失的产物 |
|---|---|---|---|
| OpenMP | *无开关*（无条件探测，缺则 HAVE_OpenMP=0） | — | 仅失加速 |
| OpenEXR | `WITH_OpenEXR` | ON | pfsinexr / pfsoutexr |
| ImageMagick (Magick++ MagickCore) | `WITH_ImageMagick` | ON | pfsinimgmagick / pfsoutimgmagick / pfsouthdrhtml |
| NETPBM | `WITH_NetPBM` | ON | pfsinppm / pfsoutppm |
| TIFF | `WITH_TIFF` | ON | pfsintiff / pfsouttiff |
| Qt5 (Widgets) | `WITH_QT` | ON | pfsview（+ pfsv 脚本） |
| MATLAB | `WITH_MATLAB` | ON | Matlab MEX |
| OpenGL + GLUT (+`find_path(GL/gl.h)`) | `WITH_pfsglview` | ON | pfsglview |
| FFTW (FindFFTW: 需 fftw3 + fftw3f + **fftw3_threads**) | `WITH_FFTW` | ON | pfstmo_durand02 / fattal02 / ferradans11 加速 |
| GSL | `WITH_GSL` | ON | pfstmo_mantiuk08 |
| OpenCV | `WITH_OpenCV` | ON | pfsalign |
| EXIF (libexif) | *无开关*（无条件探测；与 OpenCV 同时满足才编 pfsalign） | — | pfsalign |
| Octave (`find_program mkoctfile`) | `WITH_Octave` | ON | .oct/.m + pfsoctavelum/pfsoctavergb/pfsstat |
| HDRVC | `WITH_HDRVC` | **OFF**（上游默认即关） | — |
| `find_program`: bash / perl | *无开关* | — | 脚本注入 @BASH_PATH@/@PERL_PATH@ |

**关闭全部可选依赖的 -D 选项（配方 build 段实际写入 generate()）**：
```
-DWITH_OpenEXR=OFF -DWITH_ImageMagick=OFF -DWITH_NetPBM=OFF -DWITH_TIFF=OFF
-DWITH_QT=OFF -DWITH_MATLAB=OFF -DWITH_Octave=OFF -DWITH_pfsglview=OFF
-DWITH_FFTW=OFF -DWITH_GSL=OFF -DWITH_OpenCV=OFF -DWITH_HDRVC=OFF
-DBUILD_SHARED_LIBS=OFF
```

- **FetchContent / ExternalProject / file(DOWNLOAD)**：**无**（全仓 grep 0 命中）。`execute_process` 仅 3 处，均为本地探测（`octave-config`×2、`mexext`、`chmod cygmex.sh`），**无在线拉取雷**。
- **上游测试入口（R51 第 1 步清点）**：
  - `enable_testing` = **0**，`add_test` = **0**，`include(CTest)` = **0**
  - 无 `test/`、`tests/` 目录（全仓目录名含 test 的仅 `src/matlab/pfs_test_shell.m` 与文档 `doc/pfs_format_spec.tex`，均非测试套件）
  - ⇒ **上游确无测试**，附上述清点证据；可运行验证只能靠 test_package 的消费者冒烟（见 test_package/test.sh）。

## W0 依赖只读核验（recipe 层，非二进制层）
命令与结果（`conan download <pkg>/<ver> -r ohpcd --only-recipe`，日志 `~/tmp/uc2/pfstools/w0-conan-download.txt`）：

| 依赖 | 命令 | RC | 结论 |
|---|---|---|---|
| zlib | `conan download zlib/1.3.1 -r ohpcd --only-recipe` | 0 | recipe 已发布（2ee7c0ee… 2026-07-06） |
| fftw | `conan download fftw/3.3.10 -r ohpcd --only-recipe` | 0 | recipe 已发布（df2c2f06… 2026-07-29） |
| ncurses | `conan download ncurses/6.5 -r ohpcd --only-recipe` | 0 | recipe 已发布（69914b9d… 2026-08-08） |
| gsl | `conan download gsl/2.8 -r ohpcd --only-recipe` | 0 | recipe 已发布（46fe7f32… 2026-07-29） |
| libtiff | `conan download libtiff/4.7.0 -r ohpcd --only-recipe` | 0 | recipe 已发布（e12dec52… 2026-09-07） |
| libexif | `conan download libexif/0.6.26.1 -r ohpcd --only-recipe` | 0 | recipe 已发布（3a4bced0… 2026-08-16） |

- **依赖缺口：无**（且本初稿 `requirements()` 为空，核心构建零依赖）。
- **二进制层不作结论**（R35：未用 conan list 判 binary；本表只证 recipe 已发布）。
- 说明：台账候选里的 **curses/ncurses 在 pfstools 源码中无任何踪迹**（全仓 grep curses/ncurses/pdcurses 0 命中，find_package 面也无）—— pfstools 不需要 curses；仍按要求探测并记录 ncurses recipe 已发布。zlib 仅出现在 `cmake/FindOpenEXR.cmake`（`FIND_PACKAGE(ZLIB REQUIRED)`），`WITH_OpenEXR=OFF` 时不会触发。

## 语言面自证（R47 口径）
| 项 | 实测 |
|---|---|
| `.cpp` 文件数 | 108 |
| `.c` 文件数 | **1**（`src/getopt/getopt.c`，971 行 — Windows getopt fallback） |
| `.h` 文件数 | 54 |
| `.cpp` 行数 | 36919 |
| `.c` 行数 | 971 |
| C/C++ 行占比 | cpp **97.4%**（36919/37890），≥70% 阈值 |
| 构建系统 | CMake |

⇒ 主语言 **cpp**，与任务声明（cpp）**一致**；c↔cpp 属兼容族。**无语言不匹配红线。**

## 已知风险与待构建段验证点
1. **CMake 2.8.8 vs CMake≥4**（知识库 E103 症状族：`Compatibility with CMake < 3.5 has been removed`）。配方已预置 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（对 3.x 无害）。**待实测**：CI/设备 cmake 版本决定该行是否必需；若实测为 3.x，可删并在本文件记录。
2. **`check_cxx_source_compiles` 三处**（OpenMP 分支预测探测 `HAS_BRANCH_PEDICTION`、`HAS_GETOPT`）—— 交叉编译下只编译+链接不运行，**无 try_run 雷**（不触发 E159）。
3. **getopt**：OHOS/clang 应有 `<getopt.h>` ⇒ 走系统 getopt，不编 `src/getopt/`（`HAS_GETOPT` 探测决定）。
4. **`pfsin/pfsout/pfsindcraw` 及 camera 脚本**依赖 `find_program(bash)`/`find_program(perl)`：构建环境须能在 PATH 找到 bash（`/data/service/hnp/bin/bash`）与 perl，否则 sed 替换注入空路径 → 脚本不可用（perl 缺失上游仅 warning：pfsinhdrgen/pfsinme 多重曝光功能失效）。**构建段需确认 perl 是否可用**。
5. **test_package/test.sh 为初稿**：PFM 往返（`pfsinpfm in.pfm | pfsoutpfm > out.pfm`）与 `-h` 返回码未实测，构建段须实测校正。
6. `WITH_TIFF` 的 else 分支有上游笔误（`set(NETPBM_FOUND OFF)` 应为 TIFF 相关），不影响 OFF 配置（NETPBM 已另行 OFF）。

## 交付物清单（本轮落盘）
- `archives/p/pfstools/manifest.yaml`（软件级）
- `archives/p/pfstools/README.md`
- `archives/p/pfstools/commands.json`（R38，38 个 CLI）
- `archives/p/pfstools/2.2.0/conanfile.py`
- `archives/p/pfstools/2.2.0/conandata.yml`
- `archives/p/pfstools/2.2.0/manifest.yaml`（版本级，status=pending）
- `archives/p/pfstools/2.2.0/notes.md`（本文件）
- `archives/p/pfstools/2.2.0/test_package/{conanfile.py,test.sh,MANIFEST.yml}`

## 证据文件（非构建段，主理-11 在 A 机 ~/tmp/uc2/pfstools/ —— B 机无此目录，跨机不共享）
- `pfstools-2.2.0.tgz`（源 tarball）
- `w0-conan-download.txt`（W0 六项命令 + RC）
- `src/pfstools-2.2.0/`（解压源码，供构建段复用）
## 构建段实测（2026-09-24，主理-23，构建机 B）

### 门禁命令与退出码
| 命令 | RC | 结论 / 证据 |
|---|---|---|
| `bash ci/scripts/preflight_check.sh pfstools/2.2.0` | 0 | 预检通过（requirements 为空，无依赖需检查） |
| `ohc-run.py lang-preflight pfstools 2.2.0 --lang cpp` | 0 | detected=cpp（源文件 113 个，主体占比 96%），与任务语言一致 |
| `ohc-run.py recipe-search pfstools` | 0 | catalog 6175 配方，top1 即本包骨架 |
| `ohc-run.py conan-verify pfstools 2.2.0` | 0 | G1/G0/G2/G3 PASS；⚠ **G4/L2/L4/L5 报 PASS 实为「跳过（无 cache 路径）」**（工具取不到 package id），未实际执行 |
| `ohc-run.py finish pfstools 2.2.0 built` | **2** | W3 阻塞门禁**通过**（`.ci-result.json` exit_code=0）；rc=2 来自 step5b finalize 警告 + step8 gen_summary 框架崩溃（见下） |
| `ohc-run.py graph validate` | 0 | 540 对 doc↔kv 完整，All checks passed（169 条全库性告警，非本包引入） |

W3 本地 CI 模拟（`reports/w3-local-ci.log`，跑的是 CI 同款 `ci/conan/build_and_test.sh`）：
`G0_RESULT=pass`、`L0_RESULT=pass`、`L1_RESULT=pass`、`L2_RESULT=pass`、`L4_RESULT=pass`、`L5_RESULT=pass`、
`KC_RESULT=pass`、`JC_RESULT=pass`，含 **L1e 破坏性反向验证通过**（test 确实依赖被测包）。

### 交接留下的四个未决点 —— 实测结论

**① CMake `cmake_minimum_required(2.8.8)` 与设备 cmake：此行不可删，且注入方式必须改。**
- 设备 cmake = **4.1.2** ⇒ 首轮 G2 FAIL 首错：
  `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake.`
- 关键取证：该轮 cmake 命令行 RUN 行里**没有** `-DCMAKE_POLICY_VERSION_MINIMUM` ⇒ 初稿用的
  `tc.variables[...]` 只落到 toolchain 的 `set()`，而 `cmake_minimum_required()` 读的是 **cache**。
- 改为 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"` 后 RUN 行出现该 `-D`，G2 PASS。
  证据：`reports/conan-create.log` 两轮 RUN 行对比（旧 `p/b/pfsto6c747f821c63d` 前一轮止于 configure）。
- ⇒ 「实测 3.x 可删」的前提不成立：**删掉此行 CI 必红**。

**② `find_program(bash / perl)`：两者均命中，无 warning 路径。**
- CMakeCache 实测：`BASH_EXECUTABLE:FILEPATH=/data/service/hnp/bin/bash`、
  `PERL_EXECUTABLE:FILEPATH=/data/service/hnp/bin/perl`（perl 5.42.0）。
- 安装后 shebang 抽查（`~/tmp/uc2/z23-pfstools/inspect.out`）：pfsin / pfsout / pfsindcraw / pfsinme /
  pfsplotresponse / dcraw2hdrgen / jpeg2hdrgen 注入 `/data/service/hnp/bin/bash`；pfsinhdrgen 注入
  `/data/service/hnp/bin/perl -w`；包内**无残留** `@BASH_PATH@` / `@PERL_PATH@`。
- ⚠ 新发现（上游硬编码，非探测）：`pfs_automerge` 用 `#!/bin/bash`、`pfs_split_exposures.py` 用
  `#!/usr/bin/python3`，而本设备 `/bin/bash` 与 `/usr/bin/python3` **均不存在**
  ⇒ 二者执行返回 **rc=127**（`No such file or directory` 指向解释器）。

**③ `test_package/test.sh`：初稿三处与实测不符，已按真机行为全部校正。**
1. **管道方向反了**：`pfsoutpfm` 从 **stdin 读 PFS**、把 PFM **写到位置参数命名的文件**。
   初稿 `pfsoutpfm stream.pfs > out.pfm` 因此把 `stream.pfs` 当输出文件覆写，`out.pfm` 为空 ⇒ 这正是首轮
   `FAIL: pfsoutpfm produced empty output` 的根因。实测正确形态 `pfsoutpfm rt.pfm < s.pfs` 产出 26B，
   且 16 字节像素 payload 与输入 `cmp` 逐字节相同。
2. **`-h` 不是 help**：`pfscat -h` = horizontal、`pfscat` 无文件时要求 `--vertical/--horizontal`；
   `pfssize` 无 `--xsize/--ysize`，真实选项是 `--x / --y / --ratio`；上游 `--help` 统一 **返回 rc=1** 并打印 usage。
3. **不能用输出文本判可执行性**：conan 以 test_package 目录为 cwd，bash 在其中 `getcwd()` 失败并打印
   `job-working-directory: ... cannot access parent directories: No such file or directory`，
   与「解释器缺失」的错误串撞车 ⇒ 第二版脚本据此误判 6 个 bash 脚本工具 FAIL（44/50）。
   校正：改用 **rc=127/126** 判不可执行，并在 `test_package/conanfile.py` 用 `self.run(..., cwd=<~/tmp 临时目录>)`
   消除 getcwd 噪声。
- 另记上游数据面事实：`pfsinpfm` 对 `Pf`(3 通道) 头部实际按 **1 通道** 读（2x2 得 4 个 float），
  `pfsoutpfm` 恒写 `Pf` 魔数（实测 rt.pfm = 10B 头 + 16B payload）。测试断言因此只锁「像素 payload 逐字节保真」，
  不声明通道数语义。

**④ `commands.json` 与实际产物逐项对齐（集合差已做）。**
- 实装 `bin/` 共 **40** 个产物；原申报 38。
- 漏报（补入）：`pfstmo_durand02`、`pfstmo_fattal02` —— `WITH_FFTW=OFF` 只是失去 FFT 加速，二者仍被编译安装。
- 虚报（删除）：`pfs_automerge`、`pfs_split_exposures.py` —— 文件在但**不可执行**（rc=127，见未决点②）。
- **最终申报 38 个，全部真机实测 rc∉{126,127} 且 usage 输出非空**（审计表 `~/tmp/uc2/z23-pfstools/cli-audit.txt`）。
- 可选整改（未做，超出本任务口径，交主理决策）：给上游两个脚本的 shebang 打
  `#!/usr/bin/env bash` / `#!/usr/bin/env python3` 补丁即可救回 2 个命令（会变成 patches/ CI 输入 + 需复跑 W3）。

### 测试口径（五维账本）
| 维度 | 上游 | test_package（消费者） |
|---|---|---|
| 静态声明总数 | **0**（`enable_testing`=0 / `add_test`=0 / `include(CTest)`=0，无 `test/`、`tests/` 目录） | 44 |
| 可执行数 | **0**（无测试入口，R51 清点证据见上） | 44 |
| 实测通过数 | **0** | **44** |
| 跳过数 | 0 | 0 |
| 失败数 | 0 | 0 |

- 上游侧是**真 0**，不是省略：pfstools 2.2.0 无任何测试套件（未跑 `make check`/`ctest` 亦无从跑起）。
- test_package 44 条构成：38（命令存在性+可执行性）+ 3（PFM→PFS→PFM 往返保真）+ 1（pfsgamma 数值
  0.25^(1/2.2)=0.5318 → 小端 `44 53 08 3f`）+ 2（pfssize `--x 4 --y 4` 与 pfscat `--vertical` 尺寸链）。
- 数字同源：`reports/w3-local-ci.log` 内 conan create 真实执行的 `ASSERT_TOTAL=44 / ASSERT_PASS=44 / ASSERT_FAIL=0`。

### 构建段新发现的风险（未擅自处置）
1. **SourceForge 源站在 B 机不可达（CI 下载风险）**。15:23 phoenixnap 镜像曾成功取回（614772B，sha256 与
   conandata 一致），15:25 起 conan create 在 `source()` 停滞 10 分钟零字节；实测 canonical URL `http=000`、
   `downloads.sourceforge.net` 302 落到死镜像 `twds.dl.sourceforge.net`、ufpr/jaist DNS 解析失败(rc=6)。
   **CI 的 mirror fallback 对 SourceForge 分支 `return [url]`，不加任何镜像**（`ci/conan/build_and_test.sh` L1117-1120），
   仅靠 predl 的 `curl --retry` ⇒ 若 CI worker 同样不可达会红。
   本轮处置：**环境侧** conan sources 缓存（`core.sources:download_cache=$HOME/tmp/ch/dlcache`，键为 sha256）
   命中已通过二次校验的官方 tarball；**`conandata.yml` 保持官方单条 URL 未改**（`git diff` 已核）。
   若需要配方侧加固，可把 `url` 改为官方多镜像列表（conan `get()` 原生支持逐个 fallback，
   L0j 归一化也已考虑列表形态）—— 属 CI 输入变更，等主理拍。
2. **`finish` step8 `gen_summary` 崩溃**：`gen_summary 失败: 'str' object has no attribute 'append'`
   （框架侧，非本包引入；改框架需独立 PR，本窗口不动 `scripts/`）。
3. **submit 就绪预检 2 项未满足**：`packaging/`（无 release/debug tar.gz）与 `.staging-verified`。
   本轮走 recipe-first，未做 mode B staging；**不为过门禁造假产物/空标记**。
   `reports/test-report.md` 已按实测结果补建。
4. **conan-verify 的 G4/L2/L4/L5 是「跳过」不是「实测通过」**：其取 package id 失败（`无法找到程序包 ID`）
   ⇒ 真正的 L0-L5 证据以 W3 跑的 `ci/conan/build_and_test.sh` 日志为准。

### 知识引用与 B 判定
- 引用的既有条目：`E092`（CMake 不识别 HarmonyOS —— OHOS 版 conan 已自动映射，本包无需处理，G0 已识别为已处理）、
  `E103` / `E187`（CMake 4 移除 <3.5 兼容的症状族与 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 方案）、
  `E447`（其 rec_command 已载 `tc.cache_variables[...]` 的正确注入形态）。
- **B 判定：`none`**（维持台账初判）。理由：本段撞上的两个机制都**不是新机制** ——
  CMake4 policy 注入形态已被 E103/E187/E447 覆盖；「上游源站真机不可达 + sha256 校验的预下载/源缓存」
  在库内已有同族草稿 `knowledge/drafts/libdisasm-0.23-sourceforge-unreachable-predl-file-url.kv`。
  ⇒ 按「一 PR 一知识、重复不建」不新建 B 草稿。

### 构建段过程记录（对话/决策时间线）
- 15:22 验盘：HEAD `e4ab5d71a`，`origin/main..HEAD` 恰 1 行，仅 libXext 大小写幻影为 modified（未触碰）。
- 15:23 取证：B 机原无 A 机取证副本（跨机不共享）⇒ 自行按 conandata URL 取回，sha256 与声明值逐字一致（未改哈希）。
- 15:25 首起 conan create（GATE_PASS，长杆槽）⇒ 15:35 取证 `source()` 停滞：source 目录空、进程 `S (sleeping)` 于 EVENTPOLL、3 个 socket 无进度。
- 15:44 镜像面复测：全部 SourceForge 端点不可达（rc=6/28/35）⇒ 判定为网络/源站问题，不归因 OHOS/工具链/上游。
- 15:53 环境侧源缓存命中重跑 ⇒ G2 FAIL 首错 = CMake <3.5 兼容移除；据 RUN 行定位 `tc.variables` 不注入 cache。
- 15:54 改 `tc.cache_variables` 并提交；15:56 起 G2 过 configure/build/install，败于 test_package。
- 15:57–16:05 逐条实测 CLI 语义（`--help` rc、pfscat/pfssize 真实选项、pfsoutpfm 管道方向、PFM 通道行为），
  产出 `cli-audit.txt`（40 个产物的可执行性审计）。
- 16:06 提交 `9bce200c3`（配方 + commands.json + 第一版 test.sh）并推送 origin。
- 16:08 定位第二版 test.sh 的误判根因（getcwd 噪声撞车错误串）⇒ 改 rc 判据 + `cwd=` 传参，独立预跑 44/44。
- 16:12 conan-verify **RC=0** 全绿；16:18 finish（W3 阻塞门禁通过，status→built）；16:22 graph validate RC=0。

### 构建段证据文件（B 机 `~/tmp/uc2/z23-pfstools/`）
- `verify.out` / `verify2.out`（下载停滞轮）/ `verify3.out`（CMake policy 轮）/ `verify4.out`（断言误判轮）/ **`verify5.out`（RC=0）**
- `finish.out`（10 步全量）、`EVIDENCE-01-download-stall.md`（停滞首错取证包）
- `cli-audit.txt`（40 产物可执行性审计）、`bin-actual.txt` / `bin-declared.txt`（commands.json 集合差）
- `inspect.out`（shebang / CMakeCache BASH·PERL / 占位符残留）、`pfmprobe.sh` + `shebangs.txt`
- `src/pfstools-2.2.0.tgz` + `sha256.txt`（官方源取回副本）、`cmds-ok.txt`（38 个实测可执行命令）
- `conanfile.py.orig-bak`（改前配方备份）
- 归档内日志：`reports/conan-create.log`、`reports/w3-local-ci.log`、`reports/conan-verify-report.md`、
  `reports/test-report.md`、`.ci-result.json`（exit_code=0，含 log_sha256，禁止手改）
- 环境侧（非 PR 内容）：`$CONAN_HOME=$HOME/tmp/ch/home-z23-pfstools`（global.conf 增
  `core.sources:download_cache=$HOME/tmp/ch/dlcache` 一行）
## 构建段补记（收尾复核，2026-09-24 16:35）
### 新证据：CI 的 predl 通道在本机可取回 SourceForge 官方源（风险 1 降级）
W3 跑的 `ci/conan/build_and_test.sh` 自带 Pre-download（`curl --retry` + 镜像列表），
其产物留在 `.build-cache/predl_cache/`：

```
ef2bac57_pfstools-2.2.0.tgz   614772 bytes
sha256 = 9bf6844985663226c21998eeb43c261acb8e4b3891b9a91b729554406289d7ca   ← 与 conandata.yml 声明值逐字一致
```

⇒ 与本轮的另一条实测并看：conan 自带的 `get()` 下载器在 15:25 对同一 URL **停滞零字节**，
而 CI 的 predl 在 16:21 **成功取回同哈希文件**。
故风险 1 由「CI 可能下不到」修正为：**conan 裸下载不稳，CI 的 predl 路径实测可用**；
配方保持官方单条 URL 的做法与本仓库的 CI 设计一致，无需在 conandata 里塞镜像。
（本机侧本轮靠 `core.sources:download_cache` 命中，属环境加速，不影响 CI。）

### ⚠ 框架缺陷留档：predl 的 `file://` 还原 trap 未生效
第二轮 `finish`（16:32）跑完后，`archives/p/pfstools/2.2.0/conandata.yml` 在工作区被留在

```
url: "file:///storage/Users/currentUser/qzy/主理-23-pfstools-2.2.0/.build-cache/predl_cache/ef2bac57_pfstools-2.2.0.tgz"
```

而 `build_and_test.sh` 里本应有 `trap _restore_conandata EXIT` 还原官方 URL
（脚本注释写明动机是「防止 file:// 残留被提交，gulkan PR #7121 被 W4 判 P0 打回」）。
- 备份确实生成了：`.build-cache/predl_cache/conandata.yml.predl-orig` 内容是官方 URL；
- **还原没有发生** ⇒ 若下一次提交用 `git add -A`/`commit -a` 之类的整树操作，就会把 `file://` 提交进 PR（P0/P1 级）。
- 本轮处置：`git show HEAD:...conandata.yml > ...conandata.yml` 还原（不用 checkout/restore），
  复核 `url` 已回到官方值、`git status` 对 `archives/p/pfstools` 干净；
  已提交的 HEAD（`e4ab5d71a..906acb6e8`）**全程未包含 file:// 形态**（`git diff` 证据：差异只在工作区）。
- 已顺手删除本窗口自建的 `.build-cache/`（纯下载缓存 + 备份，可重建，非用户资产）。
- ⇒ 建议：这是 `ci/conan/build_and_test.sh` 的框架问题，**须另开框架 PR**，不在本配方 PR 内改。
  另外提醒后续窗口：**本包收尾一律用精确路径 `git add -- archives/p/pfstools`**，正好是这条缺陷的防线。

### 最终 HEAD 与验证绑定关系
- 提交链：`e4ab5d71a`（初稿）→ `9bce200c3`（配方/commands.json/test.sh 实测修正）
  → `8a3a969a7`（构建段台账）→ `906acb6e8`（finish 复跑收口）→ 本补记所在收尾提交
- `conan-verify` RC=0 与 W3 `exit_code=0` 对应的 CI 输入集合
  （conanfile.py / conandata.yml / test_package/ / commands.json）与 `906acb6e8` **内容一致**
  （conandata.yml 的 `file://` 属工作区污染，已还原；notes/manifest 非 CI 输入，其后的改动不影响验证绑定）。
---

**编译结束**: 2026-09-24 16:38
**最终状态**: built
