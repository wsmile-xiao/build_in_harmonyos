# fceux 2.6.6 适配笔记

## 编译环境

- 构建系统: cmake（上游 Qt/SDL 端口唯一构建入口，`CMakeLists.txt` + `src/CMakeLists.txt`）
- 编译日期: 2026-09-09
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（待真机预检回填实测证据后由 HMBS 统一提交）

## 上游信息

- 上游仓库: <https://github.com/TASEmulators/fceux>
- 上游版本: v2.6.6（2023-08-26 维护版本；官网下载页源码包即该 GitHub tag 归档）
- 源码包: `https://github.com/TASEmulators/fceux/archive/refs/tags/v2.6.6.tar.gz`（22.2MB，实测下载）
- sha256: `0320241d45c6d609f7aeb6f85fdd9019552047206b0864a7f9fddff15b004daa`（curl 下载 22.2MB 归档后 `certutil -hashfile SHA256` 实测）
- 许可证: GPL-2.0-or-later（`COPYING`，package() 复制到 `licenses/`）

## 编译步骤

Qt5 应用标准流程（flameshot 14.0.0 先例）：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部关键动作（`conanfile.py`）：

1. `requirements()`: `qt5-qtbase/5.15.2.2` + `sdl2/2.30.10` + `zlib/1.3.1.1`（override）+ `bzip2`/`expat` RREV override；minizip 1.3.1 为内置 vendored（无外部 requires）；
   `build_requirements()`: `pkgconf/3.0.5`（上游 `find_package(PkgConfig REQUIRED)`）。
2. `generate()`: CMakeDeps（`qt5-qtbase` 映射 `cmake_file_name=Qt5`）+
   PkgConfigDeps（供上游 `pkg_check_modules(sdl2/minizip/...)` 发现 registry 包）；
   不生成 conan CMakeToolchain（ML-0035：OHOS 下映射值不被真机 cmake 识别，
   改走自发现 `ohos.toolchain.cmake` + 裸 cmake，expat/zstd 先例）。
3. `build()`: `cmake.configure()` 显式传入 `Qt5_DIR`/`CMAKE_PREFIX_PATH`/
   `CMAKE_FIND_ROOT_PATH`（OHOS SDK toolchain 把包查找限制在 find-root 内，
   flameshot 先例）、`CMAKE_AUTOMOC/RCC/UIC_EXECUTABLE`（指向 qt5-qtbase 的 moc/rcc/uic）、
   `CMAKE_AR/RANLIB`（SDK 自带路径修正），`--parallel 1`（真机内存保护）。
4. `package()`: `cmake.install()` 安装 `bin/fceux` + 桌面文件/man 页/auxlib.lua。

## 上游测试审计（结论：无可接入测试）

审计方法：下载 v2.6.6 源码包，解压后全文检索测试入口。

| # | 位置 | 发现 |
|---|------|------|
| 1 | `CMakeLists.txt`（顶层，仅 `add_subdirectory(src)`） | 无 `enable_testing`/`add_test` |
| 2 | `src/CMakeLists.txt`（约 400 行，硬依赖 Qt5/SDL2/ZLIB/minizip） | 无 `enable_testing`/`add_test`/`add_custom_target(check)` |
| 3 | `tar -tzf \| findstr test` 全包检索 | 唯一命中 `NewPPUtests.txt`（PPU 测试说明文档，非可执行用例） |
| 4 | `pipelines/linux_build.sh`（上游官方 Linux 构建脚本） | 仅 `ldd` + 打包 + `dpkg -i`，无任何测试命令 |
| 5 | `pipelines/` 其余脚本、`azure-pipelines.yml` | 无测试步骤 |

结论：上游不存在可接入的测试套件。`test_package/MANIFEST.yml` 已按规范写入
`upstream_tests_exist: false` + 非空 `upstream_test_audit`，test_package 在执行
消费者测试后重放 `HMBS_UPSTREAM_TEST_RESULT`（`status: no_tests`），
主配方 `build()` 不重复发射标记（c10t 先例：cache 命中轮次 build 输出可能被跳过）。

## test_package 设计（R34 合规）

上游 `src/drivers/Qt/fceuWrapper.cpp` 在参数解析阶段即处理：

- `--help`/`-h` → 直接 `exit(0)`
- `--version` → 打印 `2.6.6` 后 `exit(0)`

两者均在进入 Qt 事件循环前返回，因此可用 `QT_QPA_PLATFORM=offscreen`
在无头真机执行（flameshot/augustus-game 的无头 `--version` 模式同理）。
`test_fceux.sh` 共 2 个用例：`--version` 输出含 `2.6.6`、`--help` 退出码 0；
`conanfile.py` 解析脚本尾部 `RESULT: P passed, F failed` 行，
据实发射 `HMBS_TEST_PACKAGE_RESULT`（含必填 `discovered`/`passedCount`），
失败时抛 `ConanException` 使 `conan create` 变红（先证伪：无 RESULT 行即判 harness 损坏）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游硬依赖 Qt5/SDL2，OHOS 是否可满足 | 需确认制品仓有已发布配方 | 已确认：`qt5-qtbase/5.15.2`、`sdl2/2.30.10`、`minizip/1.3.1`、`zlib/1.3.1` 均有完整配方目录 |
| 2 | 上游 `pkg_check_modules(... REQUIRED sdl2/minizip)` 如何命中 Conan 包 | CMakeDeps 只生成 CONFIG 包，不生成 .pc | 增加 PkgConfigDeps 生成器 + `pkgconf/3.0.5` tool_requires（cairomm/gulkan 先例） |
| 3 | OHOS SDK toolchain 下 `find_package(Qt5)` 找不到 CMakeDeps 生成的配置 | SDK 设置 `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY` | `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH` + generators 目录传入 `Qt5_DIR`/`CMAKE_PREFIX_PATH`/`CMAKE_FIND_ROOT_PATH`（flameshot 先例） |
| 4 | Qt GUI 二进制在无头真机无法进入事件循环 | 无显示服务 | 用 `QT_QPA_PLATFORM=offscreen` + 上游原生 `--version`/`--help` 早退出口做冒烟测试 |

## 依赖版本

- qt5-qtbase/5.15.2.2（Qt Widgets + OpenGL 前端；基线 5.15.2 在制品仓无 OHOS
  二进制，真机预检 "No compatible configuration found"，全仓 Qt 消费方统一
  5.15.2.2；本包无 qt5-qtsvg 冲突，用 plain requires，quazip/1.4.1 同式）
- sdl2/2.30.10（SDL2 音频/视频/输入后端）
- minizip 1.3.1 内置（vendored：zlib-1.3.1 contrib/minizip 静态编译，自产 minizip.pc；无外部 requires）
- zlib/1.3.1.1（系统 zlib；`override=True` 全图统一 qt5-qtbase 传递的 1.3.1；
  独有版本自动落 ohpcd，gtk4/wv 同式；-fPIC 静态 libz.a 可链进共享库）
- pkgconf/3.0.5（构建期工具）
- Lua：上游内嵌 `src/lua` 静态编译（`LUA_USE_LINUX`），无外部依赖
- libarchive/x264/x265/ffmpeg/X11/xkbcommon：可选缺失，上游自动降级关闭对应功能

## 验证结果

待 HMBS 真机预检回填（本轮仅完成未提交工作树，未执行真机验证）：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期：构建通过；test_package 输出 HMBS_TEST_PACKAGE_RESULT（2/2）与
# HMBS_UPSTREAM_TEST_RESULT（no_tests）；PR 正文通过率以预检日志实测为准
```

## 本轮真机预检失败分析（2026-09-10，fixing_verification）

首轮预检（`conan create`，`--build=missing`）失败阶段为 compile，直接证据：

- `qt5-qtbase/5.15.2: No compatible configuration found`——制品仓无该基线版本
  的 OHOS 二进制，后续只能走 Qt5 源码构建；
- `bzip2/1.0.8: CMakeToolchain generated ... cmake.configure(...)` 后
  `Configuring incomplete, errors occurred!`——进入依赖图的 bzip2 配方是
  CMake 构建（仓内 `archives/b/bzip2/1.0.8` 为 Makefile 构建、无 `generate()`），
  即解析到的不是 OHOS 适配配方，在 `CMAKE_SYSTEM_NAME=HarmonyOS` 下配置失败；
- 顶部另有 `preflight.sh: can't create temporary file /tmp/*.tmp: Read-only
  file system` 与 HMBS `[readonly_tmp]` 诊断——本包配方与 test_package 均只写
  构建目录/`TMPDIR`（test_package 显式使用 `TMPDIR`/`TEMP` 可写拷贝），不写
  `/tmp`；该诊断指向依赖构建或 harness 层，本轮在配方侧无可改点，仅作记录，
  若下轮预检顶部仍出现同类 harness `/tmp` 错误则按真机环境问题上报。

根因判定（基于本轮实际核查，非推测）：

1. `qt5-qtbase/5.15.2` pin 错误：全仓 20+ 处 Qt 消费（flameshot 14.0.0、
   quazip 1.4.1、neovim-qt、ElaWidgetTools 等）统一使用 `5.15.2.2`，
   基线 `5.15.2` 无二进制。已改为 `5.15.2.2` plain requires（本包无
   qt5-qtsvg 带来的版本冲突，无需 flameshot 式的 override + 手工
   include/link 注入；quazip 同为 Qt5+zip 的 CMake 包，照抄其范式）。
2. `zlib` 保持与 qt5-qtbase 自身声明一致的基线 `1.3.1`（qt5-qtbase/5.15.2 与
   /5.15.2.2 均 `requires("zlib/1.3.1")`），避免双版本冲突；conan-center 无
   `zlib/1.3.1` 与 `minizip/1.3.1`（仅有 1.3.2/1.2.13），故二者均解析到 ohpcd，
   无 CCI 配方污染（已用 CCI config.yml 实证）。
3. 残留风险（配方侧无法消除，需下轮预检验证）：依赖图中的 `bzip2/1.0.8`
   无 OHOS 适配父项——仓内 `minizip`/`sdl2`/`zlib`/`pkgconf`/`qt5-qtbase`
   配方均无 bzip2 依赖，指向制品仓某依赖的已发布 revision 与仓内配方不一致
   （registry hygiene 问题）。若下轮 bzip2 仍在图中且失败，升级为上报：
   请求先重新发布 minizip/1.3.1（R36 依赖先行），本 PR 不做配方外 hack。

## 本轮策略变更（2026-09-10 第二轮，同一指纹第 2 次修复）

上一轮（直接依赖换版 `qt5-qtbase/5.15.2→5.15.2.2`）后预检呈现**同一失败指纹**
（`bzip2/1.0.8: cmake.configure(build_script_folder=...source_folder, pardir)`
→ `System is unknown to cmake` → `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
→ `ConanException: Error 1`），证明直接依赖 pin 不是 bzip2 失败的根因。
按防重复要求，本轮改用不同路线：**传递依赖的 RREV override 图手术**，
不再触碰直接依赖版本。

- 新证据（第二轮日志）：`qt5-qtbase/5.15.2.2` 成功从 ohpcd 解析（revision
  `760fc7d9...`），其传递 `dbus/1.14.10` 亦来自 ohpcd；`expat/2.8.2` 与
  `cmake/4.4.3` 来自 conancenter（CCI expat 无二级依赖，与 bzip2 无关）。
  仓内 `minizip`/`sdl2`/`zlib`/`pkgconf`/`qt5-qtbase`/`dbus` 配方均无 bzip2
  依赖，故 bzip2 必来自制品仓某依赖的已发布旧 revision（与仓内配方不一致），
  默认 remote 顺序下命中 CCI CMake 配方（`build()` 第 62 行即
  `cmake.configure(...)`，仓内 Makefile 配方无此行——铁证）。
- 方案：`self.requires("bzip2/1.0.8#3b49a968338a1932917a5049fce54a4e",
  override=True)`，把全图 bzip2 强制到 cataract/1.0.0 已合入（main 分支、
  `status: built` 2026-09-02，CI L0i 的 `conan download -r=ohpcd` 已验证该
  RREV 存在）的 OHOS revision。conan 按精确 RREV 取包，不再走 remote 顺序
  命中 CCI。fceux 本体不链接 bz2，仅做图手术；test_package 口径不变。
- 观察项（未失败不预修）：`expat/2.8.2` 来自 CCI，若其 OHOS 构建失败，
  下一轮参照 cataract 的 `expat/2.8.2.1#332af6a48367eceadb1f9cf0c32f340d`
  做同式 override；`dbus`/`qt5` 源码构建耗时久但为必经之路（全 Qt 消费方同态）。

## 第三轮：bzip2 override 生效，失败前移到 CCI cmake（2026-09-10）

第二轮的 bzip2 RREV override 被验证有效：本轮预检 bzip2 不再构建失败
（`Checking remote: conancenter / ohpcd` 后正常解析，失败指纹消失，
fceux 包 ID 随 requirements 变化而更新也证实新配方已同步上机）。
新失败点为 `cmake/4.4.3: Error in build() method, line 35 ... KeyError: 'OHOS'`。

- 链条：`qt5-qtbase/5.15.2.2 → dbus/1.14.10（ohpcd）→ expat/2.8.2` 在默认
  remote 顺序下命中 conancenter 修订版；CCI expat 的 tool_requires 把
  CCI `cmake/4.4.3` 拉入闭包，而该修订版 conandata 按 OS/架构分源，
  无 `OHOS` 条目，直接 `KeyError`。与 bzip2 同类（CCI 修订版无 OHOS 支持），
  但位置从普通依赖变为 tool_requires，属新失败域——不是重复上轮修改，
  而是把已验证有效的 RREV-override 手法推广到下一环。
- 方案：`expat/2.8.2.1#332af6a48367eceadb1f9cf0c32f340d` override（cataract
  同式，已合入）。ohpcd 该修订版 `requirements()` 为空、无 tool_requires，
  CMake 直调宿主工具链（hmbs 提供 `cmake` 可执行文件）+ `ohos.toolchain.cmake`，
  自带 `.so` 自签名逻辑；一次性同时消除 CCI expat 与 CCI cmake 两处源码构建。
  expat API 跨 `2.8.2→2.8.2.1` 稳定（ohpcd 后缀即同上游源码 + OHOS 修复），
  dbus 经 pkg-config 消费不受影响。
- 下一观察项：`dbus`（ohpcd autotools 配方）与 `qt5-qtbase` 源码构建为必经
  之路；`zlib`/`sdl2`/`minizip`/`pkgconf` 二进制或快速源码构建应无碍。
  若 dbus 构建失败再按失败日志处理，不提前预修。

## 第四轮：zlib CCI CMake 失败，改用版本后缀唯一化路线（2026-09-10）

前三轮的 RREV-override 手法对 bzip2/expat 已验证有效（失败指纹逐轮前移），
但本轮新失败 `zlib/1.3.1: CMakeToolchain generated ... cmake.configure()`
→ `System is unknown to cmake` → `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
→ `Configuring incomplete` 证明 `zlib/1.3.1` 同样命中 conancenter CCI 修订版
（其 `build()` 第 81 行即 `cmake.configure()`；仓内 `archives/z/zlib/1.3.1`
为 Makefile 配方，无 `generate()`/CMake——铁证）。按第 4 策略周期要求，
本轮不再沿用 RREV 哈希路线（RREV 存在多版本：mcrypt 实证 `90ec87…`、
glib 实证 `2ee7c0ee…`，本地复算易错；libgsf/pycairo 均记录复算与制品仓
不一致的坑），改用版本后缀唯一化路线：

- 方案：`self.requires("zlib/1.3.1.1", override=True)`。`1.3.1.1` 为仓内独有
  版本（同上游 1.3.1 源码 + `-fPIC` 静态重建，`manifest.yaml` 明示；
  conancenter 无 `1.3.1.1`，自动落 ohpcd，无需 RREV 哈希；
  `gtk4/4.22.4`、`abiword-plugin-*`（override）、`wv/1.2.9`（force）、
  `bamtools/2.5.3` 同款）。`override=True` 把 `qt5-qtbase/5.15.2.2` 传递的
  `zlib/1.3.1` 全图统一到 `1.3.1.1`（zlib API 稳定；`-fPIC` 静态 `libz.a`
  反而更适合链进 Qt 共享库；仓内 `libpng`/`cairo` 下游已改指 `1.3.1.1`）。
- 附加收益：Makefile 配方不走 CMake，不写 `/tmp`，同步消除本轮 HMBS
  `[readonly_tmp]` 诊断中属于 CCI zlib CMake 构建的部分；本包配方与
  test_package 本就只写构建目录/`TMPDIR`（test_package 显式透传
  `TMPDIR`/`TMP`/`TEMP`），配方侧无 `/tmp` 硬编码，故顶部
  `preflight.sh[306]: can't create temporary file /tmp/*.tmp: Read-only`
  的 harness 层部分若下轮仍出现则按真机环境问题上报，不在配方侧改动。
- 上一方案（RREV）为何不能直接复用：RREV 需精确命中制品仓实际存在的
  修订版，而 `zlib/1.3.1` 在制品仓至少有两个历史 RREV 且本地无法查询
  当前有效值，猜错即 `Unable to find ... in remotes`（pycairo 第 8 项同款）。
  版本后缀路线无此风险。

## 第五轮：minizip CCI CMake 失败，改用 RREV pin 路线（2026-09-11）

上轮 zlib 版本后缀路线已验证生效（本轮日志 `zlib/1.3.1.1: Checking remote:
conancenter / ohpcd` 正常解析，zlib 失败指纹消失，包 ID 随 requirements 变化
更新证实新配方已同步上机）。新失败为 `minizip/1.3.1` 的同类 CMake 配置失败
（`Generators folder ... CMakeToolchain generated ... Calling build()` 后
`System is unknown to cmake` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
→ `Error in build() method, line 71`）。仓内 `archives/m/minizip/1.3.1` 为直接
编译 contrib/minizip 源码的配方（无 CMake 配置步骤），故进入依赖图的是 CCI
修订版——与 bzip2/zlib 同类（默认 remote 顺序 conancenter 在前）。

按“同一指纹第 2 次修复须换策略”要求，本轮不复用上轮版本后缀路线（minizip 在
仓内只有 1.3.1 一个版本，无独有版本可切），改用 bzip2/expat 轮的 RREV pin 手法：

- 方案：`self.requires("minizip/1.3.1#0e5742df58dfcd5e301661eb6c2f0cda")`
  （普通 requires，非 override，保证 PkgConfigDeps 仍生成 minizip.pc；
  gtk4 注释记载 override 会使直接依赖不进图）。RREV 按 conan
  FileTreeManifest.summary_hash 以 git-blob LF 内容复算
  （conanfile.py + conandata.yml 两文件；minizip 无补丁故无 export_source
  前缀；算法先用 zlib/1.3.1.1 的已验证 RREV 9a23e7d5… 校验一致）。
  minizip 在 SUMMARY 中状态为 uploaded，故该 RREV 即制品仓实际值；
  自适配提交后配方未再改动（git log 仅 3 次提交），无 libgsf R48 式的
  发布后改动导致复算不一致的风险。
- 残留观察项：`sdl2/2.30.10`、`pkgconf`、dbus/qt5 源码构建仍为必经之路；
  若 sdl2 同样命中 CCI，再按本轮同式处理，不提前预修。

## 第六轮：RREV 在远端不存在，改用 vendored minizip（2026-09-10）

上一轮 RREV pin 被真机证伪：`ERROR: Package 'minizip/1.3.1#0e5742df58dfcd5e301661eb6c2f0cda'
not resolved: Unable to find ... in remotes`。本地按 FileTreeManifest 复算的
RREV 与制品仓实际值不一致（换行符/导出内容差异均可导致此结果；此前 bzip2/expat
的 RREV 来自 cataract 已验证记录而非本地复算，故有效）。按“同一失败域换策略”
要求，本轮不再猜测 RREV（远程不可查询，猜错即重复失败），改用消除外部依赖的
路线：

- 方案：删除 `self.requires("minizip/...#...")`，在 `conandata.yml` 新增
  `minizip_sources`（与 ohpcd minizip/1.3.1 包同源的
  `zlib-1.3.1.tar.gz`，同 sha256 `9a93b2b7...`），`source()` 双下载后
  `build()` 内编译 `contrib/minizip`（ioapi/mztools/unzip/zip）为静态
  `libminizip.a`，自产 `minizip.pc`（`Requires: zlib`，`Libs: -lminizip`）
  并经 `PKG_CONFIG_PATH` 供给上游 `pkg_check_modules(MINIZIP REQUIRED minizip)`。
  版本同源、静态链接，无运行时 `.so` 待签名，也不再触发 CCI minizip 的 CMake
  构建与 `/tmp` 写入。
- 上游 `src/CMakeLists.txt` 仍走 `MINIZIP_FOUND` 系统分支（`_SYSTEM_MINIZIP`），
  仅实现位置从外部 Conan 包变为配方内置，不属功能降级；`zlib/1.3.1.1`、
  bzip2/expat override 与 test_package 口径均不变。

## 第七轮：vendored minizip 的 clang 在构建环境外启动失败（2026-09-10）

本轮预检失败阶段仍为 compile，但失败域已从依赖图前移到本配方内部，
直接证据：`fceux/2.6.6: RUN: /data/service/hnp/bin/clang -fPIC -O2 ... -c
.../minizip-src/contrib/minizip/ioapi.c -o .../vendored-minizip/obj/ioapi.o`
→ `/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found` →
`ConanException: Error 127`。此前 bzip2/expat/zlib 的 RREV/版本后缀路线均已
验证生效（失败指纹逐轮前移），vendored 方案本身的方向（消除 CCI minizip）
不变，本轮只修工具调用方式。

根因（基于源码与日志确认）：`build()` 先调 `self._build_vendored_minizip()`
再进入 `with self._build_environment().vars(self).apply():`，即直接
`self.run(cc ...)` 跑在构建环境之外。SDK clang 启动需要
`LD_LIBRARY_PATH` 指向 llvm/lib（`libxml2.so.16`，profile 注释明示缺失时
所有链接步骤失败）与任务私有 `TMPDIR`（宿主 `/tmp` 只读，日志顶部
`can't create temporary file /tmp/*.tmp: Read-only file system`），两者都只
在 `_build_environment()` 内提供；环境外直接 exec 即报 127。同時配方硬编码
SDK 绝对路径（llvm-ar/llvm-ranlib/CMAKE_AR/RANLIB），worker 间 SDK 布局变化
即失效。

方案（最小改动，不碰依赖图与测试口径）：① `build()` 改为在单个
`with _build_environment().vars(self).apply():` 内先编译 vendored minizip 再
cmake configure/build；② `_build_environment()` 透传 hmbs 注入的任务私有
`TMPDIR/TMP/TEMP`；③ 新增 zimg 式 `_resolve_tool/_tool_next_to/_exec_tool`
（conf 绝对路径存在优先，否则 PATH 查找，否则编译器同目录 sibling，脚本型
编译器经 `sh` 启动），cc/ar/ranlib/CMAKE_AR/CMAKE_RANLIB 全部经此解析，
删除所有 `/data/service/hnp/...` 硬编码。输出物（静态 libminizip.a +
自产 minizip.pc + PKG_CONFIG_PATH）与上游 `_SYSTEM_MINIZIP` 分支不变。

## 第八轮：conan CMakeToolchain 在真机报 System unknown，改用 ohos.toolchain（2026-09-10）

第七轮的环境内直调 clang 已被验证生效（本轮失败指纹前移到 `cmake.configure`
`line 336`，vendored ioapi.o 错误消失，包 ID 随配方变化更新证实新配方已上机）。
新失败域为 cmake 配置阶段，直接证据：`System is unknown to cmake` +
`The CMAKE_C_COMPILER: /data/service/hnp/bin/clang` / `CMAKE_CXX_COMPILER:
.../clang++` broken → `Configuring incomplete` → `ConanException: Error 1`。
这是与上轮不同的失败阶段（编译器直调 → cmake compiler check），按要求采用
不同策略：不再调整环境变量/工具解析，改换 CMake 工具链路线。

根因（仓内已有定论 ML-0035）：conan 的 CMakeToolchain 在 `os=OHOS` 下把
`CMAKE_SYSTEM_NAME` 映射为 stock cmake 不识别的值，真机 cmake（hmbs 注入
`/storage/Users/currentUser/usr/local/bin/cmake 4.4.3`）直接报 unknown system
且 compiler check 失败。此前 bzip2/zlib/minizip 的 CCI CMake 配方在同一 worker
以同一指纹失败，而 ohpcd 的 Makefile 配方与 expat（bare cmake）成功，
形成完整对照。expat/2.8.2.1 的 `generate()` 注释明示“不用 conan 的
CMakeToolchain”，zstd/1.5.7.1、glfw、libjpeg-turbo、opus 同法。

方案（照抄已验证先例，不自创）：① `generate()` 只保留 CMakeDeps（Qt5 映射）
+ PkgConfigDeps（sdl2/minizip .pc），删除 CMakeToolchain 生成；② 新增
`_ohos_toolchain()` 自发现（profile `user_toolchain` → `OHOS_NDK_HOME` →
glob 最新 `ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake`）；
③ `build()` 改裸 `cmake -B build-ohos -S <src> -DCMAKE_TOOLCHAIN_FILE=…
-DOHOS_ARCH=arm64-v8a …` + `cmake --build --parallel 1`，保留 Qt5_DIR/
PREFIX_PATH/FIND_ROOT_PATH、AUTOMOC/RCC/UIC、FIND_ROOT_PATH_MODE_PACKAGE=BOTH、
POSITION_INDEPENDENT_CODE；④ `_cmake_ar_ranlib()` 从 toolchain 目录派生
`llvm/bin/llvm-ar`（不存在才回退 PATH 解析），ranlib 优先 PATH 真值否则按
zstd 式生成 `llvm-ar s` 小 shim（`#!/bin/sh`，避免硬编码 bash 路径）；
⑤ `package()` 改裸 `cmake --install --prefix`。依赖图与测试口径不变。

## 第九轮：ohos.toolchain.cmake 自发现失败，改用任务内兜底工具链（2026-09-10）

上一轮（裸 cmake + 自发现 ohos.toolchain）被证伪：预检直接报
`Invalid configuration: Cannot find ohos.toolchain.cmake`，即三个旧候选
（profile user_toolchain、OHOS_NDK_HOME、`/data/service/hnp/ohos-sdk.org/*`
glob）全部未命中。按第 5 策略周期要求不再沿用“SDK 仍在 /data 下”的旧假设：
本轮日志的 `HMBS_BUILD_TOOLS` 显示 cmake/make/ninja 均来自
`/storage/Users/currentUser/usr/local/bin`，说明预检 worker 的 SDK 布局已迁移，
旧 glob 必然落空。

新路线（geogram/1.10.1 先例，不同实现）：`_ohos_toolchain()` 保留旧候选并新增
`/storage/.../ohos-sdk.org/*` glob，全部落空时不再抛错，而是按
profile compiler → OHOS_SDK_ROOT/OHOS_NDK_HOME → `/storage/.../usr/local` →
`/data/service/hnp` → PATH 顺序探测 clang（逐项打日志供下轮诊断），
生成任务内最小工具链（CMAKE_SYSTEM_NAME=OHOS、编译器绝对路径、
sysroot（若存在）、aarch64-unknown-linux-ohos triple、
TRY_COMPILE STATIC_LIBRARY）；`_cmake_ar_ranlib()` 仅对真 SDK 文件名
`ohos.toolchain.cmake` 做目录派生，兜底工具链走编译器同目录/PATH 解析。
依赖图与测试口径不变。

## 第十轮：桌面 OpenGL 在 OHOS 缺失，映射到 GLESv2/EGL（2026-09-10）

上一轮的任务内兜底工具链被验证生效（本轮日志：vendored minizip 的 ioapi.o
编译通过，cmake 配置启动，包 ID 更新证实新配方已上机）。新失败域为上游
`src/CMakeLists.txt:87 find_package(OpenGL REQUIRED)`：
`Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY
OPENGL_INCLUDE_DIR)`。这是与工具链缺失不同的失败阶段，按要求采用新策略，
不再调整工具链发现，而是处理上游依赖本身。

根因（源码与日志确认）：上游非 Windows 分支硬依赖桌面 OpenGL（GLX），而
OHOS 只提供 GLESv2+EGL（astromenace/1.10.1 同类先例）。真机日志另证实编译器
实际位于 harmonybrew Cellar
（`/storage/.../.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/bin/clang`），
旧 sysroot 探测（仅查 `<sdk>/sysroot`）报 `sysroot=-`，故同步加强探测。

方案（最小改动，保持 REQUIRED 语义，绝不静默跳过）：① `_patch_upstream_opengl_for_ohos()`
在 `build()` 内幂等替换 `find_package(OpenGL REQUIRED)` 为 OHOS 条件块——
OHOS 时 `find_library(GLESv2/EGL)` 并设 `OPENGL_LIBRARIES/OPENGL_FOUND`，
缺 GLESv2 即 FATAL；非 OHOS 保持原样；② sysroot 探测改为
`clang -print-sysroot` + 自 bindir 上溯 6 层的
`native/sysroot`、`ohos/native/sysroot`、`sysroot` 全覆盖（harmonybrew Cellar 布局），
供 GLES 头库查找。依赖图与测试口径不变。

## 第十一轮：GLESv2 裸查找落空，改用 sysroot 显式路径两段查找（2026-09-10）

上一轮的 GLES 映射方向被验证为正确路线（补丁生效，配置推进到补丁自身的
`GLESv2 not found on OHOS` 显式 FATAL，而非原来的桌面 `FindOpenGL` 缺 GLX；
sysroot 探测同步修复为 harmonybrew Cellar 的 `native/sysroot`），但裸
`find_library(NAMES GLESv2)` 在回退工具链
（`FIND_ROOT_MODE_LIBRARY=ONLY`）下搜不到库。按“同一指纹第 3 次换策略”要求，
本轮不再重复裸查找，改用两段式查找：先带 `NO_DEFAULT_PATH` 在
`${CMAKE_SYSROOT}/usr/lib`、`/usr/lib/aarch64-linux-ohos`、`/lib` 显式搜
（astromenace 同式），落空再回退默认路径搜（覆盖编译器内置 sysroot）；
GLES 头文件同式；同时打印 `CMAKE_SYSROOT` 与查找结果供下轮诊断。
补丁支持升级已打旧块的源码缓存（正则替换整个 OHOS 条件块），保持 REQUIRED
语义（缺 GLESv2 仍 FATAL，不静默跳过）。

## 第十二轮：FindZLIB 在 ONLY 根模式下看不见 Conan 包，直传 ZLIB 路径（2026-09-11）

上一轮的两段式 GLES 查找被验证生效（本轮日志 `OHOS GL lookup result:
GLESv2=.../libGLESv2.so EGL=.../libEGL.so`，配置越过 OpenGL 推进到
`src/CMakeLists.txt:164 find_package(ZLIB)`）。新失败
`Could NOT find ZLIB (missing: ZLIB_LIBRARY) (found version "1.3.1")`
是不同失败域（模块查找可见性，非工具链/GL），按要求换新路线。
根因：任务内兜底工具链设 `FIND_ROOT_MODE_LIBRARY/INCLUDE=ONLY`，
FindZLIB 只搜 `CMAKE_SYSROOT`（SDK 自带 zlib 头故报 version 1.3.1，
但库不在 sysroot 内故缺 ZLIB_LIBRARY）；Conan 的 zlib 包在 cache 内，
CMakeDeps 不提供 Module 所需变量。
方案（ettercap/freerdp 先例）：`build()` 新增 `_zlib_cmake_defs()`，
取 `self.dependencies["zlib"].package_folder`，显式传
`-DZLIB_ROOT=<pkg> -DZLIB_INCLUDE_DIR=<pkg>/include
-DZLIB_LIBRARY=<pkg>/lib/libz.a`（.a 缺失才回退 .so），绕过 find 搜索。
`[readonly_tmp]` 诊断指向 harness/`/tmp` 层，本配方与 test_package 仅写
构建目录与任务私有 `TMPDIR`（`_build_environment` 已透传），无 `/tmp`
硬编码，本轮不改动。

## 第十二轮补丁（同指纹第 2 次，换策略：不再查 dependencies 字典）

上一轮 `_zlib_cmake_defs()` 被真机证伪：日志
`WARN: zlib package folder missing, skip ZLIB hints` 后 cmake 命令行无任何
`-DZLIB_*`，仍以同一 `Could NOT find ZLIB (missing: ZLIB_LIBRARY)` 失败。
根因：`requirements()` 中 zlib 系 `override=True` 声明——override 只统一传递
版本，不新增直接边，故 `self.dependencies["zlib"]` 查不到而跳过（ettercap 用
plain requires 故同式代码在其处有效，此处不可照搬）。
新路线（文件证据而非字典查询）：`generate()` 的 PkgConfigDeps 已在
generators 目录写出 `zlib.pc`，其 `prefix=` 即 zlib 包目录；`build()` 改为先
解析 `zlib.pc` 取包根，落空才试字典与全图扫描，仍找不到则抛
`ConanInvalidConfiguration`（绝不静默跳过 REQUIRED 依赖）。
`[readonly_tmp]` 同上轮：配方侧无 `/tmp` 硬编码，不改动。

## 第十二轮第三修（同指纹第 3 次，换策略：不再用 Conan 包，自建 vendored libz）

第二修（解析 `zlib.pc`）同样被证伪：日志
`Invalid configuration: zlib package folder not found
(generators=.../generators)`——override-only 的 zlib 节点连 `zlib.pc` 都不生成，
字典与文件两条路都走不通。按要求换第三种路线：不再找 Conan 包，
直接用已下载的同源 `zlib-1.3.1` 源码（`minizip-src` 根即 zlib 根，与 ohpcd
minizip 同源同版本）在构建环境内编译静态 `libz.a`（15 个核心 .c，
`-fPIC -O2`，`llvm-ar rcs`，与 vendored minizip 同式）+ 头 + 自产 `zlib.pc`；
`_zlib_cmake_defs()` 改为指向该 vendored 前缀（`ZLIB_ROOT/INCLUDE_DIR/LIBRARY`），
minizip 改含 vendored zlib 头，`PKG_CONFIG_PATH` 追加 vendored-zlib 的 pc 目录。
上游仍走 `find_package(ZLIB)` 系统分支（`ZLIB_FOUND`），仅实现位置内化，
不属功能降级；`zlib/1.3.1.1` 的 override（统一 qt5 传递版本）保留不动。

## 第十三轮：Qt 老式变量为空导致 QWidget 缺失 + genGitHdr 写只读 /tmp（2026-09-11）

上一轮的 vendored libz 路线已被验证生效（本轮日志越过 `src/CMakeLists.txt:164`
的 ZLIB 失败：`-- Using System minizip 1.3.1`、`Found sdl2, version 2.30.10`，
配置完成并进入 `cmake --build`）。新失败域是编译期，与之前所有
（RREV/版本后缀/vendored/工具链/GL/ZLIB）都不同，按要求换新路线。

双失败证据（同一 `conan create` 日志）：

1. `scripts/genGitHdr.sh[13]: can't create /tmp/fceux_git_info.cpp: Read-only
   file system` → `mv: cannot stat '/tmp/fceux_git_info.cpp'`（构建脚本硬编码
   `/tmp`，命中 HMBS `[readonly_tmp]` 诊断）；
2. `moc_AboutWindow.cpp → AboutWindow.h:6: fatal error: 'QWidget' file not
   found` → `make[2]: *** ... mocs_compilation.cpp.o] Error 1`
   （AUTOMOC 本身工作——moc 已生成，说明 Qt5 包已找到；只是编译该目标时
   缺少 Qt 头搜索路径）。

根因（基于上游源码与仓内配方确认）：

1. 上游 `src/CMakeLists.txt` 用老式变量
   `include_directories(${Qt5Widgets_INCLUDE_DIRS})` +
   `target_link_libraries(... ${Qt5Widgets_LIBRARIES} ...)`；
   而 `qt5-qtbase/5.15.2.2` 的 `package_info()` 只声明现代
   `cmake_file_name`/`cmake_target_name`（`Qt5::Widgets` 等），CMakeDeps
   只生成现代 imported targets，不提供老式 `_INCLUDE_DIRS/_LIBRARIES`
   变量，故两者为空（flameshot 注释亦明示 override 下 CMakeDeps 的 Qt
   路径为空；quazip/flameshot 均用现代 `Qt5::` 目标故不受影响，
   fceux 是唯一老式用法的 Qt 消费方）。
2. `scripts/genGitHdr.sh` 首行即 `TMP_FILE="/tmp/$FILE"` 写死，
   worker 宿主 `/tmp` 只读，配方 `_build_environment()` 透传的任务私有
   `TMPDIR` 对它不可见（脚本不读该变量）。

方案（最小改动，保持 REQUIRED 语义，不跳过任何测试）：

1. 新增 `_patch_upstream_githdr_tmpdir()`：仅把 `TMP_FILE="/tmp/$FILE"`
   改为 `TMP_FILE="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/$FILE"`（只换临时根，
   生成/比对逻辑不动；幂等）。
2. 新增 `_patch_upstream_qt_targets_for_ohos()`：在上游已有的
   `target_link_libraries(${APP_NAME} ...)` 块后追加守卫式
   `if(TARGET Qt5::Widgets) target_link_libraries(${APP_NAME}
   Qt5::Widgets Qt5::Gui Qt5::Core) endif()`（`OHOS_QT5_MODERN_TARGETS`
   标记保证幂等；经该 target 的 INTERFACE 自动带入头与库，
   同时修复编译与链接；缺 target 时不静默替代）。
3. `build()` 另加 flameshot 式兜底：按真实 `qt5-qtbase` 包目录计算
   `-DCMAKE_CXX_FLAGS="-I<include> -I<QtWidgets> -I<QtGui> -I<QtCore>"` 与
   `-DCMAKE_EXE_LINKER_FLAGS="-L<lib> -lQt5Widgets -lQt5Gui -lQt5Core"`
  （无硬编码路径；即使 target 补丁因源码缓存顺序未命中也能编译链接）。

## 第十四轮：SDL.h 缺失 + moc 继承断裂 + 源码下载超时（2026-09-11）

本轮预检三证据（同一 `conan create` 日志）：

1. `source()` 首跳 `ConnectTimeoutError(github.com:443)`，10 秒后重试下载
   23.3MB 成功——下载链路抖动，按守则“源码包下载超时是例外”必须把
   `conandata.yml` 的 `url` 改为有序镜像列表（官方 URL 留最后回退，
   复用 `ci/conan/build_and_test.sh` 的 GitHub 映射）。
2. `ConsoleViewerSDL.h:11:10: erro...`（`#include <SDL.h>` 行 include 位置，
   即 `SDL.h file not found`），随后同 TU 内 `QWidget::size()/cursor()/
   setMinimumSize()/setMaximumSize()` 报派生类到基类无转换、
   `moc_ConsoleViewerSDL.cpp:87/88/93` 的 `static_cast<ConsoleViewerBase*>`
   与 `QWidget::qt_metacast/qt_metacall` 同错。
3. 同包 `AboutWindow` 的 moc 已过（单 TU  unity 构建按序编译，首错停在
   ConsoleViewerSDL），说明编译器侧 Qt -I 已生效，SDL -I 与 moc 侧 -I 缺失。

根因（源码与先例确认）：

1. sdl2 包头在 `<pkg>/include/SDL2/SDL.h`（augustus-game/4.0.0 同版本
   `_header_dir` 先例即先探 `include/SDL2`），而上游仅靠
   `add_definitions(${SDL2_CFLAGS})` 传 `-I`（add_definitions 本为传 `-D`，
   脆弱），且 PkgConfigDeps 的 `sdl2.pc` 未必带 `/SDL2` 后缀目录——
   裸 `#include <SDL.h>` 解析失败。
2. `CMAKE_CXX_FLAGS` 的 `-I` 与 `add_definitions()` 的 `-I` 都到不了 AUTOMOC
   的 moc 调用（moc 只取 target INCLUDE_DIRECTORIES + MOC_OPTIONS），
   moc 缺 Qt/SDL 解析根即生成错误的 `qt_metacast` 基类转换。
   上轮 Qt5:: 链接 shim 只保证编译器侧，不覆盖 moc 侧。

方案（最小改动，无状态、不向源码烘焙绝对路径；依赖图与测试口径不变）：

1. `conandata.yml`：`sources` 与 `minizip_sources` 的 `url` 改为有序列表
   `[gh-proxy.com/<原URL>, <原URL>]`（CI 脚本 GitHub 映射原文复用，
   sha256 不变）。
2. 新增 `_patch_upstream_sdl_pkgconfig_includes()`（幂等）：在上游
   `add_definitions( ${SDL2_CFLAGS} -D__SDL__ )` 后追加
   `include_directories(${SDL2_INCLUDE_DIRS})`（同文件 X11 即此用法；
   目录级 include 同时供给编译与 automoc）。
3. `build()`：augustus 式 `_conan_header_dir("sdl2", "SDL.h", "SDL2")`
   探测，把 SDL 目录并入原 Qt 手工 `-I` 集合，一份经
   `-DCMAKE_CXX_FLAGS` 给编译器，一份经新增
   `-DCMAKE_AUTOMOC_MOC_OPTIONS="-I..;-I.."` 给 moc（AUTOMOC 原生支持，
   随构建重算，无跨 worker 缓存污染）。

## 第十五轮：timeStamp.cpp 硬编码 x86intrin 在 aarch64 下编译失败（2026-09-11）

本轮预检失败阶段仍为 compile，但失败域是首次进入的新文件
`src/utils/timeStamp.cpp`（此前 Qt/SDL/ZLIB 均已通过，配置完成并进入
`cmake --build`；`--parallel 1` 首错即停）。直接证据：

- `In file included from .../timeStamp.cpp:21: .../x86intrin.h:13: .../ia32intrin.h:200:10:
  error: use of undeclared identifier '__builtin_ia32_readeflags_u32'`，
  随后 `crc32intrin.h`、`mmintrin.h:14:2: error: "This header is only meant
  to be used on x86 and x64 architecture"`，共 20 errors，
  `make[2]: *** [... timeStamp.cpp.o] Error 1`。

根因（源码与日志确认）：上游 `src/utils/timeStamp.cpp` 在非 WIN32 分支无条件
`#include <x86intrin.h>` 并调用 `__rdtsc()`；OHOS SDK clang 目标为
aarch64，无法解析 x86 专有头。上游 issue #663 官方修复（commit 3960962）
仅以 `__QT_DRIVER__` 守卫——但 Qt 构建恰定义该宏，故 ARM+Qt 仍命中；
chimera-linux cports 以永不定义的 `__FCEU_X86_TSC_ENABLE` 变相全关 TSC。
本轮按“架构守卫”路线：x86/x64 保持上游原路径一字不变，其他架构
（含 OHOS armv8）改用 `CLOCK_MONOTONIC` 回退（`<time.h>` 已经由
`timeStamp.h` 引入；`readNew()` 原有的 `clock_gettime(CLOCK_REALTIME)`
与 `tsc = rdtsc()` 语义不变，回退仍给出有效单调计数值，
`tscCalibrate()` 不会除零）。

方案（最小改动，幂等，不碰依赖图与测试口径）：新增
`_patch_upstream_timestamp_for_ohos()`，以 `FCEU_HAS_X86_TSC` 标记检查幂等，
仅替换 `#if WIN32 / intrin.h / #else / x86intrin.h / rdtsc()` 块；
`build()` 在既有 4 个补丁后调用。x86 行为与上游完全一致，
ARM 不再包含任何 x86 头。

## 第十六轮：vendored minizip 头布局与扁平 include 错位（2026-09-11）

上一轮的时间戳架构守卫已被验证生效（本轮预检越过 `timeStamp.cpp`，
一路编译到 89% 才停，包 ID 更新证实新配方已上机）。新失败域是
`src/drivers/Qt/AboutWindow.cpp:26: fatal error: 'unzip.h' file not found`
（`#include <unzip.h>` 扁平写法）——与上轮不同文件、不同根因，
按“同指纹第 2 次换策略”要求，本轮不用上游源码补丁路线，
改用构建系统头布局路线（不触碰上游任何源码）。

根因（源码与配方确认）：vendored minizip 只把 5 个公开头装到
`<prefix>/include/minizip/`（照抄 ohpcd minizip 配方布局），
自产 `minizip.pc` 的 `Cflags` 只有 `-I${includedir}`；
该组合仅能满足 `#include <minizip/unzip.h>`，满足不了上游的扁平
`#include <unzip.h>`。且上游仅经 `add_definitions(${MINIZIP_CFLAGS})`
转发 `-I`（SDL 轮已证实该通道到不了 moc），编译器侧同样缺根。
另 `unzip.h` 内含 `#include "zlib.h"`（引号式），回退需 vendored
zlib 的 `-I` 兜底（`minizip.pc` 的 `Requires: zlib` 链 + 显式 extra_incs）。

方案（构建系统层三处，不改上游源码、不改依赖图与测试口径）：
① `_build_vendored_minizip()` 改为双布局安装——5 个头同时进
`include/minizip/`（ohpcd 式命名空间）与 `include/`（Debian 式扁平，
`AboutWindow.cpp:26` 即此写法）；② 自产 `minizip.pc` 的 `Cflags`
增为 `-I${includedir} -I${includedir}/minizip`（两种写法经
pkg-config 均可解）；③ `build()` 的 `extra_incs` 追加 vendored
minizip `include`、`include/minizip` 与 vendored zlib `include`
（一份经 `CMAKE_CXX_FLAGS` 给编译器，一份经
`CMAKE_AUTOMOC_MOC_OPTIONS` 给 moc，SDL 轮同式）。

## 第十七轮：桌面 GL 立即模式在 GLESv2 下链接失败，补 GLSL 纹理四边形（2026-09-11）

上一轮的 minizip 双布局已被验证生效（本轮预检编译到 100% 才停：
`qrc_resources.cpp.o` 完成，进入 `Linking CXX executable fceux`）。
新失败域是链接期，与之前所有编译期缺头完全不同，按要求换新路线。
直接证据：`ld.lld: error: undefined symbol: glLoadIdentity/glMatrixMode/
glOrtho/glBegin/glTexCoord2f/glVertex2f/glEnd`，全部引用自
`ConsoleViewerGL.cpp.o:(ConsoleViewGL_t::paintGL())`。

根因（上游源码与真机日志确认）：`paintGL()` 用桌面固定管线立即模式
（`glMatrixMode/glOrtho` 建投影 + `glBegin(GL_QUADS)` 纹理四边形）
绘制 NES 帧；OHOS 只有 GLESv2+EGL，既无矩阵栈也无立即模式，
故目标文件可编译（Qt 头声明了入口）但链接无实现。
此前把 `OPENGL_LIBRARIES` 映射到 GLESv2/EGL 的方向正确（配置通过），
缺的只是这 7 个固定管线符号。astromenace 的 `gles_compat`
只覆盖矩阵/灯光/数组状态，不含 `glBegin/glEnd`，不可照搬。

方案（新增渲染移植，不降级功能、不碰依赖图与测试口径）：
① 新增配方自带 `gles_immediate.h/.cpp`（`exports`，与 astromenace 同式），
实现 `paintGL()` 所用的精确子集：`glOrtho` 记录投影边界，
`glBegin/glTexCoord2f/glVertex2f` 缓存一个四边形，
`glEnd()` 经 GLSL 纹理采样程序以 `GL_TRIANGLE_FAN` 画出，
NDC 由记录的 ortho 边界换算（ honoring 调用方的
`glOrtho(0, rw, 0, rh)`，非硬编码尺寸）；
`glMatrixMode/glLoadIdentity` 为配套无操作。
② 新增 `_patch_upstream_gles_immediate_shim()`（幂等，
`FCEUX_OHOS_GLES_IMMEDIATE` 标记）：把两个文件拷入
`src/drivers/Qt/`，在 `src/CMakeLists.txt` 的
`set(SOURCES ...)` 后追加仅 OHOS 生效的
`list(APPEND SOURCES drivers/Qt/gles_immediate.cpp)`；
桌面构建仍链真实 libGL（无重复符号）。
SDL/QPainter 两个视频驱动不动；默认 OpenGL 驱动在 OHOS 下可链接且
真实渲染（纹理绑定/混合状态仍由调用方控制，shim 只签发绘制）。

## 注意事项

- 本机为 Windows，`archives/l/libXext` 与 `archives/l/libxext`（仅大小写不同）
  在检出时映射为同一文件，`git status` 恒显示该处 2 文件被修改。
  该差异来自上游仓库在大小写不敏感文件系统的固有冲突，与本任务无关；
  本 PR（由 HMBS 后台提交）只应包含 `archives/f/fceux/` 路径。
- 本轮严禁 commit/push/建 PR；工作树保持未提交，等待 HMBS 真机预检。
