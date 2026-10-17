# cmake-extras 1.1 适配记录（鸿蒙 PC 积分赛 · 任务 #6528）

## 1. 版本坐标（**1.1 没有上游 tag**，坐标是 commit）

上游仓库 `gitlab.com/ubports/development/core/cmake-extras` 只有 `1.5 … 1.10`
六个 tag（取数：
`curl -s "https://gitlab.com/api/v4/projects/ubports%2Fdevelopment%2Fcore%2Fcmake-extras/repository/tags?per_page=100"`
→ `1.10 1.9 1.8 1.7 1.6 1.5`），**没有 `1.1`**。1.1 的确切坐标来自仓库自带的
`ChangeLog` 与 `debian/changelog`：

```
2017-02-09 Bileto Bot
        * Releasing 1.1+17.04.20170209-0ubuntu1 (3073762)
```

```
commit 3073762359dd5f8d3c9c037c4ff4cf550d4b35f2
AuthorDate Thu Feb 9 12:47:56 2017 +0000
Subject    Releasing 1.1+17.04.20170209-0ubuntu1
```

即 Ubuntu 打包版本 `1.1+17.04.20170209` 的 **upstream 部分 1.1** = 该 commit 的树。
按 §2「禁止用 master/main 顶替」，配方取源就锚定这个 commit，而不是任何分支头。

### 归档 URL 的两次坑与最终形态

| 尝试 | 结果 |
|---|---|
| `/-/archive/1.1/cmake-extras-1.1.tar.gz` | **404**（无该 tag） |
| `/-/archive/<40 位完整 sha>/…` | 本机 200，**真机 403**：`cf-mitigated: challenge`（CDN 把路径里的 40 位十六进制串当抓取流量拦了）；换 UA / Accept 头一律仍 403 |
| `https://gitlab.com/api/v4/projects/<id>/repository/archive?sha=<完整 sha>` | 真机 200，但落地文件名是 `archive`（CI 的 pre-download 会把 `?` 后的部分切掉，得到**无扩展名**文件，`conan get()` 无法判定解包类型）→ 弃用 |
| **`/-/archive/3073762/cmake-extras-1.1.tar.gz`（7 位短 sha 作 ref）** | **本机 + 真机各两次下载，四份字节同 sha256**；解出的顶层目录名 `cmake-extras-3073762-3073762359dd5f8d3c9c037c4ff4cf550d4b35f2/` **内嵌完整 40 位 sha**，坐标可从包内容自证 |

sha256：`7270c239dd7555dfbdd49bcd2284f0fc52333251c5583833f534de0b623d3c22`（58485 B）。
URL 末段是 `.tar.gz`，`get()` 能自行判定解包类型，无需显式 `filename=`（真机下载日志
`Sources correctly downloaded`）。

## 2. 上游 1.1 装什么、和已合入的 1.9 有什么不同

`CMakeLists.txt` 只有两条 `install(DIRECTORY ...)`，**没有 project VERSION、没有
enable_testing/add_test、也没有 Makefile**：

1. `src/` → `${CMAKE_INSTALL_DATADIR}/cmake/`：11 个 find_package "config" 扩展机制模块
   `CopyrightTest CoverageReport DoxygenBuilder FormatCode GMock GSettings
    IncludeChecker Intltool Lcov QmlPlugins gcovr`（13 个 `.cmake` + 9 个伴生数据文件）
2. `modules/` → **`${CMAKE_ROOT}/Modules/`**：5 个 deprecated include shim
   `EnableCoverageReport.cmake FormatCode.cmake QmlPlugins.cmake UseDoxygen.cmake
    UseGSettings.cmake`

**第 2 条是 1.1 独有、也是本版本适配的唯一技术难点**：`CMAKE_ROOT` 是**正在运行的
CMake 自身安装目录**的绝对路径（真机上 `/storage/Users/currentUser/.harmonybrew/share/cmake-4.4`），
它绕过 `CMAKE_INSTALL_PREFIX`/DESTDIR，staged install 会把文件写到包外——在 conan 的
只读包目录里等价于安装失败。上游自己后来也是这么看的：

* `c6ca8632b55b`（2016-11-30）`Move Find*.cmake modules to non-versioned cmake directory
  where they can be discovered by the "config" mode of find_package().`
* `14eeaf8ed50b`（2017-04-03，1.1 **之后**，进 1.4 的 changelog）`Drop deprecated macros`
  —— 直接删掉这条 `install(DIRECTORY "modules/" DESTINATION "${CMAKE_ROOT}/Modules/")`
  并删光 `modules/`；1.5 起的树里就没有 `modules/` 了（已核对 tag 1.9 的 `CMakeLists.txt`）。

**做法**：配方不调用 `cmake --install`（纯数据包，装 nothing to compile），把两类文件
一起落到 `share/cmake/`——模块目录 `share/cmake/<Module>/<Module>Config.cmake`，
shim 平级放 `share/cmake/<Shim>.cmake`。这正是上游那条 TODO（"migrate these to the
above tree"）的方向，且**零源码补丁**：消费者一个 `CMAKE_PREFIX_PATH=<pkg>` 就
`find_package(DoxygenBuilder)`，一个 `CMAKE_MODULE_PATH=<pkg>/share/cmake` 就
`include(UseDoxygen)`。两个路径都已在真机消费者测试里真跑（见 §4）。

其它 1.1 特有事项：

* **没有 LICENSE 文件**（1.5+ 才有）；许可证全文只在 `debian/copyright`
  → 落到包内 `licenses/copyright`，`license = "LGPL-3.0-or-later"`（该文件原文：
  `License: LGPL-3` + "or (at your option) any later version"；各 .cmake 头是 LGPL v3）。
* `install(... USE_SOURCE_PERMISSIONS)`：`check_copyright.sh`、`include_checker.py`
  在 tar 里是 `-rwxr-x---`，必须带可执行位交付（`include_checker.py` 会被
  `find_program` + `execute_process` 直接执行）→ `get(..., keep_permissions=True)`
  并在 `package()` 里按源权限位逐个 chmod。
* 上游 1.1 的两个**自身缺陷**（1.9 里 `msg` 已修、`IncludeChecker` 至今未修）：
  * `QmlPluginsConfig.cmake:8` 把 `message(FATAL_ERROR …)` 写成 `msg(FATAL_ERROR …)`
    → 缺 `qmlplugindump`（Qt）时 `find_package(QmlPlugins)` 报
      `Unknown CMake command "msg"`。
  * `IncludeCheckerConfig.cmake:50` 用 `find_package_handle_standard_args` 却
    **没有** `include(FindPackageHandleStandardArgs)` → `find_package(IncludeChecker)`
    在任意平台都报 `Unknown CMake command`。消费者侧一行
    `include(FindPackageHandleStandardArgs)` 预载即可正常工作（真机已验证）。
  两条都**不改上游源码**（不属于鸿蒙适配问题），改为在消费者测试里按错误签名精确断言。

## 3. 上游测试怎么跑、N 是多少

**上游工程自身：0 个测试目标。** 取数（在解包后的 1.1 源码根目录）：

```sh
grep -cE 'add_test|enable_testing|include\(CTest\)|add_custom_target\(check' CMakeLists.txt   # → 0
ls Makefile                                                                                    # → No such file（无 make check）
```

`examples/*/CMakeLists.txt` 里确实出现 `add_copyright_test` / `add_test`，但那是
**模块用法示例**：它们注册的用例必须由打包侧的 Debian autopkgtest 脚本驱动
（`ctest -V -R must_fail_1` 等），不是上游自带的 `make check`/CTest 入口。

**打包侧 `debian/tests/` 有 5 个 autopkgtest 脚本**（`debian/tests/control` 逐条声明
Depends）。它们在鸿蒙 PC 上跑不了的**具体**原因（逐条实测，取数见下表末）：

| 脚本 | 步骤 | 缺什么（实测） |
|---|---|---|
| `findgmock` | `cmake examples/findgmock-demo && make && ./test-suite --gtest_filter=…` | `GMockConfig.cmake` 把 googletest 源码路径**硬编码成绝对路径 `/usr/src/googletest`**（真机无 `/usr/src`，根文件系统只读、建不出来）；`debian/tests/control` 另要求 `googletest (>= 1.8.0)` 的系统包 |
| `copyrighttest` | `ctest -V -R must_fail_1 …` | `CopyrightTestConfig.cmake` 第一件事是 `find_program(LICENSECHECK licensecheck)`，缺则 `message(SEND_ERROR "Cannot find licensecheck program…")`。`licensecheck` 来自 devscripts；真机 `command -v licensecheck` → **MISSING**，制品仓 `keyword=licensecheck`/`devscripts` → **0 命中** |
| `intltool` | `cmake examples/intltool-demo && make && make install` + 4 条 `check_potfile` + 跑 `fooapp` | 需要 `intltool-update`/`intltool-merge`（真机 `command -v intltool-update` → **MISSING**，`IntltoolConfig.cmake` 用 `find_program` 找不到就 `find_package_handle_standard_args` 判 FAILED）；demo 还 `pkg_check_modules(GLIB REQUIRED glib-2.0)`，真机 harmonybrew **未装 glib**（`brew list` 无该项） |
| `doxygenbuilder` | `cmake examples/doxygenbuilder-demo` + 7 条 `xmllint --xpath` 断言 | 需要 `doxygen`（真机 **MISSING**，制品仓 `keyword=doxygen` → **0 命中**）；`xmllint` 反而有（harmonybrew libxml2） |
| `includechecker` | `cmake examples/includechecker-demo && make && make test` ×4 组参数 | demo 的 `CMakeLists.txt` 是 `pkg_check_modules(GLIB REQUIRED glib-2.0)` + `gobject-2.0`：真机 `pkg-config --exists glib-2.0` → **不存在**（`GOBJECT_ABSENT` 同样；harmonybrew `brew list` 无 glib）。`include_checker.py` 侧另有两处：shebang 是 `#!/usr/bin/env python`（python2 名），以及 `clang.cindex` 需要 `libclang` 共享库——`import clang.cindex` 在真机**其实可用**（harmonybrew llvm 自带 python 绑定 `.harmonybrew/lib/python3.14/site-packages/clang/cindex.py`），但制品仓 `keyword=clang-tools` **0 命中**，无打包的 libclang |

`debian/tests/control` 的原文依赖就是证据（`Depends: licensecheck | devscripts`、
`doxygen, libxml2-utils`、`language-pack-en, intltool, libglib2.0-dev`、
`libclang-3.8-dev, python-clang-3.8`、`googletest (>= 1.8.0) | google-mock`）。
制品仓 keyword 检索实测：`doxygen` / `licensecheck` / `devscripts` / `lcov` /
`clang-tools` 全部 **0 命中**；`glib`（2.84/2.88 系列）与 `intltool/0.51.0` **有**。

所以 **上游 N = 5（打包侧 autopkgtest 用例脚本，按 control 声明的 Tests 数），
本 PR 未运行其中任何一个**，原因逐条如上（不是「平台限制」四个字：每条都指到具体
缺失的程序名 / 硬编码绝对路径 / 制品仓 0 命中）。**这些用例是 Debian 打包层的
集成脚本，不是上游库自己的测试目标**——同库已合入的 `cmake-extras/1.9`
（PR #7653）在 `test_package/MANIFEST.yml` 里同样声明 `upstream_tests: []`，
1.9 的树里也有 `debian/tests/`（8 个脚本，比 1.1 多 gdbus/gsettings）。

**换来的是把「这些模块到底能不能用」做成真测试**：见 §4，70 条断言里有 35 条
在鸿蒙上真起 `cmake` 进程去加载被打包的模块。要把 §3 表里的脚本跑起来，得先给
一个纯 CMake 数据包挂上 `glib` + `intltool`（制品仓有）以及 `licensecheck` /
`doxygen` / `lcov`（制品仓 0 命中，需要**另立依赖任务**先适配），5 个脚本里最多只
能覆盖到 `intltool` 那 1 个——不是本任务（一库一 PR）的范围，也没有为了 CI 变绿而
偷偷关掉它们。


## 4. 真机验证（独立 CONAN_HOME，未碰共享 `~/.conan2`）

命令（`CONAN_HOME=$HOME/work/psj/ch-cmake-extras`，全新缓存 + 从共享 home 只
`cp` 一个 profile 进来；本配方零依赖，故不需要任何 remote）：

```sh
conan create archives/c/cmake-extras/1.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

结果（日志字段见 §4.2）：

* `CREATE_EXIT:0`；`cmake-extras/1.1: Sources correctly downloaded from …/3073762/cmake-extras-1.1.tar.gz`
  （sha256 由 conan 校验，值同 §1）
* 配方 rev `7f3b3938083e3b540dd5ff90a2d09b94`、包 ID
  `6b129b068851896169fae42d399fa922d239ce8a`、包 rev
  `257cdf36ebfac61bb8f4874a9017cc60`
* conan 自报打包明细：`Packaged 18 '.cmake' files` / `1 '.sh'` / `4 '.in'` /
  `1 '.astyle'` / `1 '.clang-format'` / `2 files: deps, copyright` / `1 '.py'`
  → `share/cmake/` 下 **18 个 `.cmake` + 9 个伴生数据文件 = 27 个文件**，
  外加 `licenses/copyright`；**无** `bin/`、`lib/`、`include/`（纯数据包）
* 消费者 `test_package`：**`TOTAL=70 PASS=70 FAIL=0` / `ALL TESTS PASSED`**


### 4.1 70 条断言的构成

* **结构 35 条（R34 真实产物）**：`share/cmake` 存在；11 个模块目录；11 个
  `<Module>Config.cmake`；5 个 shim 文件；`.cmake` 计数 == 18；包内文件总数 == 27；
  9 个伴生数据文件齐全；`check_copyright.sh` / `include_checker.py` 可执行位；
  `licenses/copyright` 含 LGPL；无 `examples/`、`debian/` 越界安装。
* **功能 35 条（真机起 cmake）**：
  * 6 个模块 `find_package()` 解析成功 + 各自入口 macro/function 确实被定义
    （`add_doxygen` / `add_formatcode_target` / `add_formatcode_test` / `add_schema` /
    `ENABLE_COVERAGE_REPORT`），`Lcov`/`gcovr` 断言其 `LCOV_EXECUTABLE` /
    `GENHTML_EXECUTABLE` / `GCOVR_EXECUTABLE` 变量（find_program 真跑过）
  * `Intltool`（**真机与 CI worker 结论不同，逐条实测**）：上游 `IntltoolConfig.cmake:66`
    是 `find_package(Gettext REQUIRED)`——要的是**外部 gettext 工具链**（`msgfmt`/`msgmerge`），
    不是本包的东西。真机 harmonybrew 装了 `msgfmt` → rc=0，且第 104 行的
    `find_package_handle_standard_args(Intltool REQUIRED_VARS INTLTOOL_UPDATE_EXECUTABLE
    INTLTOOL_MERGE_EXECUTABLE)` **没带 REQUIRED**，所以 `intltool-update`/`intltool-merge`
    缺失只让 `Intltool_FOUND=FALSE`、脚本继续往下跑，第 180/307/348 行的
    `INTLTOOL_UPDATE_POTFILE`/`INTLTOOL_INSTALL_TRANSLATIONS`/`INTLTOOL_MERGE_TRANSLATIONS`
    三个 function 照常定义（真机走「运行期 COMMAND 命中」）。CI worker 的 cmake 在
    `/data/service/hnp/cmake.org/cmake_4.1.2`、**无 msgfmt** → `Gettext REQUIRED` 是**致命**的，
    CMake 直接停在第 66 行、后面三个 function 根本不定义（实测 `rc=1` +
    `FindGettext.cmake:409 (find_package_handle_standard_args)` 栈帧）。
    因此这 4 条断言按**双分支**写：解析成功 **或** 失败签名精确是缺 Gettext/msgfmt；
    入口命令则「运行期命中」**或**（仅在缺 Gettext 时）包内模块文本确有 `function(INTLTOOL_*)` 声明。
    **反向对照已离线复跑**：喂进 worker 真实输出 → 4 条全过；喂进「路径没装对」一类的
    打包缺陷输出（无 gettext 签名）→ 4 条全红，即断言放宽**没有**把真缺陷一起放过
  * `CopyrightTest`：允许成功或**仅**因缺 `licensecheck` 报错，且 `ADD_COPYRIGHT_TEST` 已定义
  * `IncludeChecker`：裸加载必须失败在 `find_package_handle_standard_args`（上游缺陷签名）；
    调用方预载 `include(FindPackageHandleStandardArgs)` 后 `find_package(IncludeChecker)`
    **rc=0 且 `add_include_check` 可用**（模块内部会 `execute_process` 调包内
    `include_checker.py --version`，其输出被上游 `ERROR_QUIET` 吞掉、不作断言；这里
    真正断言的是 `find_package_handle_standard_args` 的两个 REQUIRED_VARS——
    `INCLUDE_CHECKER_EXECUTABLE`（必须靠可执行位才找得到）与 `clang`——都命中）
  * `GMock`：脚本模式下 `add_library(INTERFACE)` 需要 project 上下文，退而对包内文本
    声明 `add_library(gtest INTERFACE)` / `add_library(gmock INTERFACE)` 断言
  * `QmlPlugins`：解析结果只允许「成功」或上游 `msg()` 笔误
  * 4 个 deprecated shim `include(EnableCoverageReport|FormatCode|UseDoxygen|UseGSettings)`
    解析成功且提供对应命令（这条**直接验证了 `share/cmake/` 这个 1.1 专属布局**）

### 4.2 取证

本地/设备**双向 md5 对拍**后跑（`bash tools/cme_push.sh`，8 文件全等），日志与退出码：

```
$HOME/work/psj/cme-create2.log      全新缓存 conan create 全量日志
$HOME/work/psj/cme-create.log       复跑（含按 worker 差异修正 Intltool 断言后）
$HOME/work/psj/cme-exit.txt         CREATE_EXIT
探针：tools/probes/cme_{env,probe1..4,url,sha,test1,clean,log}.sh
启动器：tools/cme_run.sh（独立 home + 撞车检查 + nohup）
```

真机环境事实（`tools/probes/cme_env.sh`、`cme_probe4.sh`）：cmake **4.4.3**、
clang（harmonybrew/SDK）、`msgfmt/msgmerge/xgettext` 有、`doxygen/licensecheck/
intltool-update/astyle/gcc` **无**；`include(CMakeParseArguments)` 在 cmake 4.4.3 下
仍可 include（真机实测 `CPA_OK`）→ 1.1 的老 CMake 写法**不需要**为 CMake 4 打补丁。

**CI worker 环境事实（与真机不同处已实测）**：构建 #53215/worker CI-007 的日志里
cmake 在 `/data/service/hnp/cmake.org/cmake_4.1.2/share/cmake-4.1`、**`msgfmt` 无**、
**`curl` 也无**（pre-download 三条 `[fail] [Errno 2] No such file or directory: 'curl'`，
随后由 conan 自己拉源并成功：`Sources correctly downloaded from
https://gitlab.com/ubports/development/core/cmake-extras/-/archive/3073762/cmake-extras-1.1.tar.gz`
→ `Uncompressing cmake-extras-1.1.tar.gz`，sha256 `7270c239…` 校验通过 → 1.1 的短 sha 归档
URL 在 CI 侧也已实测可用，gitlab.com 不在 CI 的镜像映射表里但直连可达）。
⇒ **别按真机装了 harmonybrew gettext 就假定 CI 也有 msgfmt**；本包唯一的运行期外部工具
依赖就是 Gettext，已按上面的双分支断言处理。

## 5. 与其它会话/版本的边界

* 制品仓已有 `cmake-extras/1.9`，**没有 1.1** → 不触发 L0j/R37（`precheck` 已确认）。
* 软件级 `archives/c/cmake-extras/commands.json` 是 **M**（保留 1.9 条目，追加 1.1）。
* 主分支 `archives/c/cmake-extras/` 只有 1.9，无撞车。
* 本 PR 只动 `archives/c/cmake-extras/`（7 新 + 1 改），不碰 `ci/`、`knowledge/graph/`。
