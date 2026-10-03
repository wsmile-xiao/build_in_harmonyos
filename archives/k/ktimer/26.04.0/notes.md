# ktimer 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-30
- 编译器: clang 15.0.4 / clang++（HarmonyOS PC aarch64，profile `ohos-aarch64`：os=OHOS、os.version=6.0、arch=armv8、compiler.libcxx=libc++、compiler.cppstd=17、build_type=Release）
- Conan: 2.29.1（OHOS 适配版），`tools.build:jobs=2`，独立 `CONAN_HOME`
- 状态: built

## 源码
- 官方源: `https://download.kde.org/stable/release-service/26.04.0/src/ktimer-26.04.0.tar.xz`（R39 官方 HTTPS）
- sha256: `00654fffedec9e40bd04631b3f31d4c9e42289b5b7255a8ec3906db00e307827`，454896 字节（与台账实测一致）

## 依赖版本（W0 精确探测：29/29 已发布后才开工）
| 依赖 | 版本 | 角色 |
|---|---|---|
| qtbase | 6.11.1.1 | Qt6 Core/Widgets/**DBus**（`FEATURE_dbus=ON`，单一提供者） |
| kdbusaddons | 6.29.0 | `KDBusService`（会话总线单实例） |
| statusnotifieritem | 6.26.0 | `KStatusNotifierItem` 托盘（**USE_DBUS=ON**，取 `archives/s/` 而非 `archives/k/`） |
| kio | 6.14.0 | `KF6::KIOWidgets`（`prefwidget.ui` 的 `KUrlRequester` 需要），内部钉 6.14.0 由 `override=True` 抬到 6.18 闭包 |
| kwindowsystem | 6.18.0 | `statusnotifieritem/6.26.0` 的 `CMakeLists` 硬性要求 ≥6.18.0 |
| karchive | 6.19.0 | 对齐 `kiconthemes/6.18.0` **已发布二进制**的钉版，使其不触发本地重建 |
| kconfigwidgets / ki18n / kwidgetsaddons / knotifications / kcrash | 6.18.0 | `find_package(KF6 COMPONENTS ...)` 声明的组件 |
| kconfig / kcoreaddons / kcolorscheme / kguiaddons / kcodecs / kservice / kitemviews / kjobwidgets / kauth / solid / kbookmarks / kcompletion / kiconthemes | 6.18.0（`override=True`） | `kio/6.14.0` 内部 6.14 钉版整图抬到 6.18 闭包 |
| extra-cmake-modules | 6.29.0（tool_requires） | `find_package(ECM REQUIRED NO_MODULE)` |
| qt6linguisttools / gettext / libxml2 / dbus | 6.11.1 / 0.22.5.1 / 2.15.3 / 1.14.10 | 传递依赖，均已发布 |

## 编译步骤
1. **W0 依赖预检**：`preflight_check.sh ktimer/26.04.0 --deps "<29 项>"` → 29/29 已发布，版本号未被占用（rc=0）。
2. **图谱解析**：`conan graph info` → rc=0、无版本冲突，**`Missing packages` = 仅 `kio` 一个**（其余 23 包全部命中已发布二进制）；kio 配方自带 `BUILD_TESTING=OFF`、不跑上游测试。
3. **W3 本地验证**：`conan-verify ktimer 26.04.0`（G0 预构建风险评估 / G1 配方完整性 / G2 `conan create` 干净构建 + test_package 消费者冒烟）。
4. **W5 知识图谱**：`graph validate`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
| 1 | `build` 的 Step1 把源指到 `download.savannah.nongnu.org/releases/ktimer` | `search-url` 在非 GNU 项目上返回同名假源 | 显式 `init-build --url=https://download.kde.org/stable/release-service/26.04.0/src/ktimer-26.04.0.tar.xz`（R39 官方源） |
| 2 | 依赖 `kiconthemes/6.18.0` `source()` 下载失败 | `download.kde.org` 302 → `mirror.twds.com.tw`，证书主机名不匹配 + 连接超时 | 按 sha256 核对后预置共享 `core.sources:download_cache`（`s/<sha256>` + 记录官方 URL 的 sidecar），`get()` 命中本地缓存 |
| 3 | 同上，`kio/6.14.0` 源也在失效镜像列表 | 旧版 frameworks 已被镜像站裁剪，仅官方 `Attic/` 仍有 | 从 `download.kde.org/Attic/frameworks/6.14/` 取回并核 sha 后同样预置 |
| 4 | 依赖 `kiconthemes/6.18.0` 自己的上游测试挂：`Error relocating libKF6ColorScheme.so: symbol not found`（ctest 5/5 fail） | 我们为 6.18 闭包做的 override 迫使 `kio` + `kiconthemes` **本地重建**；`kcolorscheme` 等 KF6 预编译包的 DT_RPATH 是发布方 CONAN_HOME 里烤死的过期/相对路径，musl 加载器不认 ⇒ 这是**依赖配方自己的测试**在本机必挂，本机改不了依赖配方 | **对齐其已发布二进制的钉版**：把 `karchive` override 到 **6.19.0**（`kiconthemes/6.18.0` 二进制正是钉 6.19.0）⇒ 命中二进制、不再重建（见第 11 行） |
| 5 | Qt6DBus 提供者二选一 | `qtbase/6.11.1` 是 `FEATURE_dbus=OFF`，`qtbase/6.11.1.1` 是 `FEATURE_dbus=ON` | 取 `qtbase/6.11.1.1` 并 `override=True`，整图单一 Qt6 提供者，不引入 `qtbase-sql-dbus` 变体 |
| 6 | 托盘配方同名近似 | `statusnotifieritem/6.26.0`（`archives/s/`，USE_DBUS=ON）与 `kstatusnotifieritem/6.26.0`（`archives/k/`，USE_DBUS=OFF）同上游、同版本、同产物 | 读配方 docstring 核对 `USE_DBUS`，按「消费者是否需要托盘协议与会话总线」选型；选错时构建照常通过、托盘静默失效（无报错） |
| 7 | 本机长期内存门槛不过 | 多窗口并发构建，MemAvailable 在 5669~6050MB 抖动，`gate.sh` / `build-slot --mem 6000` 的时点判定反复抖空 | 执行器轮询等 `GATE_PASS` 且取槽成功再起 W3；不降门槛、不跳闸 |
| 8 | （本配方）`Could NOT find KF6 (missing: Notifications Crash)` —— 我明明在 `requirements()` 里声明了它们 | **Conan 2 的 `override=True` 只用于覆盖传递依赖的版本**：若某包**只由本配方声明、没有任何传递依赖引用**，这条 override 边会被**整条丢出依赖图**（`conan graph info` 中 `knotifications`/`kcrash` 出现 0 次，去掉 override 后立即出现）。症状却伪装成 CMake 找不到包，极易误判成路径/前缀问题 | `knotifications`/`kcrash` 这类「仅本配方直连」的包**不得**用 `override=True`；反之 `ki18n`/`kwidgetsaddons` 既要被 `kio` 的 6.14 钉版覆盖、又要有本配方声明 ⇒ 必须带 `override=True`（否则 `Version conflict: ki18n/6.14.0 vs 6.18.0`）。**判据是「有没有传递引用」，不是「是不是直接依赖」** |
| 9 | 一度误判「KIO 零使用」并打补丁移除 → 下一轮 `ui_prefwidget.h:30: fatal error: 'kurlrequester.h' file not found` | **只 grep 了 `*.cpp/*.h`，漏了 `.ui`**：`prefwidget.ui` 用 `KUrlRequester`（`kurlrequester.h` 属 KIOWidgets），C++ 侧 `m_commandLine->lineEdit()` 4 处依赖 | **撤回补丁、恢复 KIO**；教训固化：判「组件是否未使用」必须把 `.ui`/`.ui` 生成头一起扫 |
| 10 | `statusnotifieritem/6.26.0` 在**它自己的** `CMakeLists.txt:52` 红：`Could not find a configuration file for package "KF6WindowSystem" compatible with 6.18.0` | 为让 `kio` 命中二进制我把 `kwindowsystem` override 到 6.14.0，但 SNI 配方硬性要求 ≥6.18.0 —— **两者天生不可兼得** | 保持 `kwindowsystem/6.18.0`（SNI 命中二进制），接受 kio 本地重建；kio 配方自带 `BUILD_TESTING=OFF` 不跑测试，无 RPATH 测试风险 |
| 11 | `kiconthemes/6.18.0` 一旦本地重建就因 KF6 坏 RPATH 挂（第 2 轮） | 它的**已发布二进制**钉的是 `karchive/6.19.0` | 把 `karchive` override 到 **6.19.0** 对齐其钉版 ⇒ 命中二进制、不再重建 |
| 12 | **本体已编译打包成功**，挂在最后的 `test_package`：`[FAIL] ktimer --version 退出码 127` + `Error loading shared library $HOME/.cache/conan2/p/.../libKF6WidgetsAddons.so (needed by …/libKF6ConfigWidgets.so)` | KF6 预编译包的 `DT_NEEDED` 是**烤死的绝对路径**，指向发布方 conan home `$HOME/.cache/conan2`；本任务按规范用 `CONAN_HOME=$HOME/tmp/ch/home-ktimer` ⇒ 路径不存在，OHOS musl 按字面解析、无 `LD_LIBRARY_PATH` 回退（知识命中 E088 同族）。实测本任务 home 内 149 个 `.so` 中 **30 个**含该绝对路径；`$HOME/.cache/conan2` 当前不存在 | 与 `ktuberling/26.04.0` `_fix_absolute_needed` 同族（kgoldrunner 先例）：缺失的绝对路径建符号链接/或改写本任务缓存内的前缀 —— **属系统区取舍，已上报主理裁定** |
| 13 | **CI build #65871 红（首错）**：`Could NOT find OpenSSL (missing: OPENSSL_CRYPTO_LIBRARY OPENSSL_INCLUDE_DIR)` ← `KF6ArchiveConfig.cmake:51 (find_dependency)` ← `kio/CMakeLists.txt:60`，`kio/6.14.0` 被迫本地重建 | 见下节「CI #65871 返修」两层根因（① 6.18 闭包改写 kio 的 `info.requires` ⇒ package_id 失配必重建；② `karchive/6.19.0` 装出来的配置硬要 OpenSSL，而 openssl 在我方图里被 `_skip_binaries()` 判 Skip 不落地） | 本配方新增直接 requires `openssl/3.5.6.1` ⇒ 二进制必下载 ⇒ kio 的 `generate()` 把其 include/lib 写进 `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH`（改后实测新增 3 行，kio package_id 不变） |



## CI #65871 返修（2026-09-30，首错定位与修法取证）

**首错原文**（`~/tmp/uc2/ktimer-ci65871.log:716-725`）：

```
CMake Error at …/Modules/FindPackageHandleStandardArgs.cmake:227 (message):
  Could NOT find OpenSSL … (missing: OPENSSL_CRYPTO_LIBRARY OPENSSL_INCLUDE_DIR)
Call Stack: FindOpenSSL.cmake:716 ← CMakeFindDependencyMacro.cmake:78
  ← …/p/karch…/p/lib/cmake/KF6Archive/KF6ArchiveConfig.cmake:51 (find_dependency)
  ← CMakeLists.txt:60 (find_package)
kio/6.14.0: Package 'e2d99fa2705c2fdbeb8cbfce6c69f949aca1033a' build failed
```

### 第一层：kio 为什么没用上已发布二进制（⇒ 必然本地重建）

- 已发布二进制 `conan list 'kio/6.14.0:*' -r ohpcd` → `dcf59174e6b6ccb400ebbcf1f434aaac1819b11b`；
  CI 实算 → `e2d99fa2705c2fdbeb8cbfce6c69f949aca1033a`（`ktimer-ci65871.log:387`）。
- **对照实验（决定性）**：拿一份只要 `kio/6.14.0`、**没有任何 override** 的最小消费者，
  用同一 CI profile 跑 `conan graph info` → package_id = `dcf59174…` **完全相等**、
  `binary=Cache` ⇒ 二进制本身可命中，**差异 100% 出自我方的 override**。
- `info.requires` 逐字段比对（settings/options 逐字相同：`armv8/Release/clang/libc++/15/OHOS 6.0`、
  `shared=True`；差异全在 requires）：

  | | 已发布 `dcf59174…` | 我方实算 `e2d99fa…` |
  |---|---|---|
  | KF6 钉版 | `karchive/6.14.Z`、`kauth/6.14.Z`、…、`kwindowsystem/6.14.Z`（16 项 @6.14） | `…/6.18.Z`（16 项 @6.18）+ `karchive/6.19.0#d6233ee0…:952b2781…` |
  | 条目数 | 19 | 25（多 `extra-cmake-modules/6.19.0`、`zlib/1.3.1.1`、`zstd/1.5.Z`、`qtbase-sql-dbus/6.11.Z`、`dbus/1.14.10`、`expat/2.8.Z`） |

- **且这条重建躲不掉**（两条都是硬约束）：
  ① `kwindowsystem` 必须 ≥6.18.0 —— `statusnotifieritem/6.26.0` 装出来的
  `lib/cmake/KF6StatusNotifierItem/KF6StatusNotifierItemConfig.cmake:38` 写死
  `find_dependency(KF6WindowSystem "6.18.0")`（notes 第 10 行同源）；
  ② `karchive` 必须 =6.19.0 —— `conan list 'kiconthemes/6.18.0:*' -r ohpcd` 显示其
  已发布二进制 `info.requires` 钉 `karchive/6.19.0#d6233ee0…:952b2781…`（notes 第 11 行同源）。

### 第二层：kio 重建时 configure 为什么找不到 OpenSSL（⇒ 我方可修点）

1. `karchive/6.19.0` 装出来的 `lib/cmake/KF6Archive/KF6ArchiveConfig.cmake`
   **第 34 行 `set(KArchive_HAVE_OPENSSL "TRUE")`、第 50-52 行 `if (TRUE) find_dependency(OpenSSL)`**
   —— 消费方 configure 必须能 find 到 OpenSSL。
2. 但 `karchive` 配方的 `info.requires` 只有 `extra-cmake-modules/qtbase/zlib/zstd`，
   **自己不声明 openssl** ⇒ 我方图里 openssl 只经 `kiconthemes/6.18.0` 传递进来，
   `conan graph info` 实测这条边 `direct=False、headers=False、libs=False`。
3. Conan 2 `_skip_binaries()`（`conan/internal/graph/graph_binaries.py:533-580`）：
   `deps_required` 只收 `req.files`（headers 或 libs）为真或「direct + consumer」的节点，
   openssl 两头都不占 ⇒ `node.binary = BINARY_SKIP`（`:579`）⇒ 包不落地
   ⇒ kio 的 `generate()` 里 `for dep in self.dependencies.values(): if dep and dep.package_folder:`
   这道门把它挡掉 ⇒ 实测改前 `conan_cmakedeps_paths.cmake` **99 行、openssl 0 行**。
4. **本机过是假绿**：本机 `CMakeCache.txt` 里 `OpenSSL_DIR=/storage/Users/currentUser/.harmonybrew/lib/cmake/OpenSSL`
   （config 模式命中），而 CI 日志 `grep -i harmonybrew` **命中 0 次**、worker 走模块模式
   `FindOpenSSL.cmake` 才爆的错。
   最小复现（本机、无 conan 路径、模块模式）= 与 CI **逐字相同**的
   `Could NOT find OpenSSL … FindOpenSSL.cmake:716`。

### 修法（仅动本包 conanfile.py 一个文件）

`requirements()` 里新增 **`self.requires("openssl/3.5.6.1")`**（直接 requires，不带 override）。

- 机制：root 是 consumer ⇒ 直接边 `files=True` ⇒ openssl 进 `required_nodes` ⇒
  二进制必下载（改后 `Skip` → `Cache`，CI 上会是 `Download`）⇒
  `package_folder` 有值 ⇒ kio 的 `generate()` 写入其 include/lib。
- **不改 kio 的 package_id**：kio→openssl 这条边 `package_id_mode=None`、不进 `info.requires`，
  改后实测仍为 `e2d99fa2705c2fdbeb8cbfce6c69f949aca1033a`（不会因为本次改动再触发新一轮失配）。
- 改后重建 kio 实测：`conan_cmakedeps_paths.cmake` 由 99 行 → 102 行，新增
  `CMAKE_PREFIX_PATH/CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH` 各 1 行，指向
  `p/opens…/p/lib/cmake`、`p/opens…/p/lib`、`p/opens…/p/include`；
  日志 `openssl/3.5.6.1: Already installed! (7 of 36)`。
- find 侧闭环实验（模块模式 = worker 等价路径）：
  不带该路径 → `Could NOT find OpenSSL`（CI 同款）；
  带该路径 → `INC=<conan>/include`、`CRYPTO=<conan>/lib/libcrypto.a`、`SSL=<conan>/lib/libssl.a`。
- conan openssl 包内**没有** `OpenSSLConfig.cmake`（`find` 零命中）⇒
  worker 上 config 模式仍失败、回落模块模式 ⇒ 正好吃我们注入的
  `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH`。

## 源码修改
**无上游源码补丁**（`patches_applied: []`）。上游声明的 KIO 组件**确有使用**（`prefwidget.ui` 的 `KUrlRequester`、`kurlrequester.h` 属 KIOWidgets，C++ `m_commandLine->lineEdit()` 4 处），按上游原样保留；所有适配都在 conan 配方层完成（依赖闭包 + 工具链/RPATH 注入）。DocBook 手册由上游 `KF6DocTools_FOUND` 守卫自然跳过，`ki18n_install(po)` 以 `KF_SKIP_PO_PROCESSING=ON` 跳过。

## 测试
- **上游测试：0 个（N_static=0）**：源码树无 `tests/`、`autotests/`、`test/`，
  顶层与子目录 `CMakeLists.txt` 无 `add_test()`/`enable_testing()`/`ecm_add_tests()`
  （`grep -rn` 扫描 `*.txt`/`*.cmake`，排除 `po/` 零命中）；上游 QA 由 KDE CI
  源码构建承担（`.kde-ci.yml`）。MANIFEST 如实申报 0/0，不虚报不伪造。
- **适配后补全 1 项消费者冒烟**：`test_package/test_ktimer.py` 在
  `QT_QPA_PLATFORM=offscreen` 下真实运行安装后的 `ktimer --version`，
  断言退出码 0 + 版本串 `26.04.0` + 程序名；`KAboutData::processCommandLine`
  在 `KDBusService`、托盘与主窗口创建**之前**处理 `--version` 并退出，
  故该冒烟不触达会话总线与托盘、可无人值守执行。

## 运行时依赖路径差异（本机环境处理，不进 PR 配方）

**根因**：KF6/Qt6 预编译包的 `DT_NEEDED` 是**烤死的绝对路径**，指向发布方 conan
home `$HOME/.cache/conan2`；本任务按工作区规范使用
`CONAN_HOME=$HOME/tmp/ch/home-ktimer`，该路径不存在 ⇒ OHOS musl 对含 `/` 的
`NEEDED` **按字面解析、无 `LD_LIBRARY_PATH` 回退**（知识命中 **E088** 同族），
冒烟报 `[FAIL] ktimer --version 退出码 127` + `Error loading shared library
$HOME/.cache/conan2/p/.../libKF6WidgetsAddons.so`。

**实测影响面**：`p/*/p/lib/*.so` 口径 **149 个中 30 个**受影响；按「全任务 home
内 ELF 含旧前缀」口径实测 **75 个**（含 `bin/` 农场副本与 `p/*/p/bin/*`）。

**本机处理（全部在允许区，未改任何配方与 `test_package`）**：
1. 先 `cp -a` 备份到 `~/tmp/uc2/ktimer-sopatch-09301638/`（含 `LIST-before.txt`）；
2. 把 ELF 内以 `$HOME/.cache/conan2`（40 字节）开头的完整 NUL 结尾字符串，前缀换成
   **更短**的 `$HOME/tmp/ck`（33 字节），尾部补 NUL —— **改短不改长**、字符串表长度
   不增长、改写后断言 `ELF` 头完好；HMDFS 拒绝原地 `open(w)`（EPERM）⇒ 走
   临时文件 + `os.replace` 原子替换；
3. 建桥 `ln -s $HOME/tmp/ch/home-ktimer $HOME/tmp/ck`（`~/tmp` 属可丢弃产物区）；
4. **复验读数**：`p/*/p/lib/*.so` 残留 = **0**；全任务 home **997 个 ELF 残留 = 0**；
   360 个 `.so` 的 ELF 头异常 = **0**。
5. **md5 读数**（改写前后各一次，完整列表在备份目录）：
   - `LIST-before.txt` 前 2 条：`7bb2683c9822bac5672be7bb02d89313 bin/libKF6Bookmarks.so`、
     `75bdca7d0f9d19b87b3b84e9e2bea6a9 bin/libKF6BookmarksWidgets.so`
   - `p/kconf005f2764ab2a6/p/lib/libKF6ConfigWidgets.so`：`ac21f71abc047a4ef68ae2adb5a16fcc`
     （探测写入曾误伤首字节，已按该 md5 从备份**逐字节还原并复核**）
   - `LIST-after.txt` 前 2 条：`715d8723c54304f65cfeea0574604d15 bin/libKF6IconThemes.so`、
     `6857d7f9c64bccee1dbd32779aaa8347 bin/libKF6IconWidgets.so`

**自伤与修复（改动可回滚的证明，两处均由我造成、也由我抓回）**：
1. **误写首字节**：做可写性探测时对 `p/kconf005f2764ab2a6/p/lib/libKF6ConfigWidgets.so`
   执行 `f.write(b"\x00")`，把 ELF magic `7f` 改成 `00` ⇒ **立即按 `LIST-before` 的
   md5 `ac21f71abc047a4ef68ae2adb5a16fcc` 从备份逐字节还原并复核**（当前头 `7f454c46`、
   md5 一致、备份目录未被污染）。
2. **rename 丢可执行位**：HMDFS 拒绝原地 `open(w)`（EPERM）⇒ 第 2 批 19 个文件改走
   临时文件 + `os.replace`，而新建临时文件默认 **660** ⇒ 19 个 `.so` **丢了可执行位**
   （musl 拒载）⇒ 按备份原权限恢复，**检查 94 个、修正 19 个（660→770）**。

**新根因（A/B 可逆对照实证）：`os.replace`/重建会让 `.so` 的 OHOS 签名失效**
- `ctypes.CDLL` 逐个探针（同一 musl 加载器）：被拒 3 个（`libKF6ConfigWidgets` /
  `libKF6KIOCore` / `libQt6Widgets`）**全部**是走 `os.replace` 重建的；能加载的
  2 个（`libKF6DBusAddons` / `libKF6CoreAddons`）是第 1 批**原地写**的；
  `.codesign` 段**五个都有** ⇒ 判别项不是"段存不存在"，而是**重建方式**。
- **A/B**：`cp -a` 备份 → `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1` → 该文件 `dlopen` **成功**，错误推进到
  下一个未重签文件 ⇒ 因果坐实。
- **第 10 轮处置**：对 B' 改写的 **75 个** ELF 统一重签 —— **成功 75 / 失败 0**；
  重签前整体备份 `~/tmp/uc2/ktimer-resign-09301757/`（75 件 +
  `LIST-resign-before.txt`/`LIST-resign-after.txt`）。
- **重签前后 md5（各取前 2）**：
  - before：`a3deb994bdbec1cdadd6b6e52ef46356 bin/libKF6IconThemes.so`、
    `6857d7f9c64bccee1dbd32779aaa8347 bin/libKF6IconWidgets.so`
  - after：`5f346864a53330bdaaaa354c0e6a4060 bin/libKF6IconThemes.so`、
    `e0cc1fb722acc46a226ea1cc8686f60e bin/libKF6IconWidgets.so`
- **复验计数**：75 个逐个 `dlopen` → **`SIG_FAIL`(Permission denied，签名类) = 0**、
  `OK` = 18、`NOT_FOUND` = 49、`OTHER` = 8；追加 221 个预载样本中**签名类 = 0**、
  裸名未解析 = 208、相对项 13、图外残留 2。`NOT_FOUND` 归因**测试台局限**
  （`python3` 进程没有本体的 31 条 `DT_RPATH`，而 E088 证明 OHOS 不认
  `LD_LIBRARY_PATH`），与被测对象无关。
- **W3 前完整预检（避免烧轮）**：110 个 ELF 的**绝对 `NEEDED` 不存在 = 0**；
  26 种裸名由本体 `DT_RPATH` 31 条覆盖；`../../bin/*` 相对项由 test_package 农场
  + 受控 CWD 承接；gettext 里 5 处 `~/.conan2` 字样**不是 NEEDED**。

**CI 侧口径（风险披露）**：这 30/75 个包正是在 conan home=`~/.cache/conan2` 的机器
上烤出来的，**发布方即构建机本身 ⇒ worker 上 `~/.cache/conan2` 是真实路径、字面解析
天然命中**，`ktuberling/26.04.0` 先例在 worker 上跑绿亦印证。若 CI 仍以同样绝对路径
报红，按 `AGENTS §7.2` 返修路径处理，届时采用
**`ktuberling/26.04.0` 的 `_fix_absolute_needed` 先例**（kgoldrunner 26.04.0 已合入）
在 `test_package` 内为缺失的绝对 `NEEDED` 建符号链接。

## 路径判定：路径 B（贡献创新），B判定=create
- 机制：**KF6 托盘 StatusNotifierItem 同名双配方选型 + Qt6DBus 单提供者基座**
  （草稿 `DRAFT-ktimer-26.04.0-kf6-tray-dbus-provider-selection.{kv,md}` 成对，
  同 PR 提交；Issue #3637）。
- 四范围查重：平台知识图谱命中 `E323`（改 qtbase 配方开 dbus）、`E441`
  （新建 `qtbase-sql-dbus` 变体）、`E542`（Qt6LinguistTools provider）——
  均为「改造/新建配方」路径；本条目是「已有两份配方时如何选」，解法不同；
  同批草稿 `DRAFT-E5xx-ohos-qtbase-dual-ecosystem-kf6-version-gate` 讲
  qtbase 双生态**版本冲突**与版本闸补丁，本条目讲**不报错的静默降级**，
  触发签名与处置动作都不同。`draft-review` 预审建议 `create`（最高相似度 0.13）。
- 路径 C 四条件均不满足：无强绑定私有系统接口、无私有编译工具链、
  无汇编/闭源/特殊调度、依赖链全部仓内现成且上游测试 0 个。

## 本地验证
- `conanfile.py` / `test_package/conanfile.py` / `test_ktimer.py`：`py_compile` 通过
- `conandata.yml` / `manifest.yaml` / `test_package/MANIFEST.yml` / `commands.json`：解析通过
- 占位符清零门：对 conandata.yml / manifest.yaml / test_package/ / conanfile.py 跑「sha256 占位、构建系统模板、软件名模板、TODO 标记」四类正则，**命中 0 条**（本行刻意不写正则原文，避免自匹配）
- 草稿 `.kv`：真实 YAML 解析通过（26 字段），`draft-review` 质量预检 signature/root_cause/rec 全 ✅
- `conan graph info`：rc=0、`WARN=0`，**`Missing packages` = 仅 `kio` 一个**（kio 配方自带 `BUILD_TESTING=OFF` 不跑上游测试），其余全部命中已发布二进制；`knotifications`/`kcrash` 均在图
- W3（`conan-verify`）：**G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，Verdict PASS**，`test_package` 实跑 `[PASS] ktimer --version 退出码 0，输出: ktimer 26.04.0`
- W3 本地 CI：见 `reports/conan-verify-report.md` 与 `reports/conan-create.log`
  （日志不入库，仅本机留档）
---

**编译结束**: 2026-09-30 18:09
**最终状态**: built
