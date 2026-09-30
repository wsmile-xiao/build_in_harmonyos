# libalkimia 8.2.1 适配笔记（HarmonyOS PC）

## 基础信息

| 项 | 值 |
|---|---|
| 上游 | KDE alkimia https://invent.kde.org/office/alkimia |
| 源码 | https://download.kde.org/stable/alkimia/8.2.1/alkimia-8.2.1.tar.xz |
| sha256 | `f921410e180e0a5811e1ee2926954920c6576a72b3b65f53791faa6c85fcb689`（本地 `sha256sum` 实测一致） |
| 语言/构建 | C++17 / CMake（ECM、KDEInstallDirs） |
| Conan 包 | `libalkimia/8.2.1`（`package_type = library`，`shared=True`） |
| package_id | `6b7c1d6cde4058c65ff7653f2a20abed47f06b0d` |

## 命名口径（平台任务名 = Conan 包名 = 归档目录名）

平台任务 #13041 的包名是 `libalkimia`（taskBranch `feat/libalkimia-8.2.1`），
而 KDE 上游模块名是 `alkimia`、安装的 CMake 包名是 `LibAlkimia6`。因此：

- 归档目录：`archives/l/libalkimia/8.2.1/`（`l` = 包名首字母）
- `conanfile.py`：`name = "libalkimia"`，`class LibAlkimiaConan`
- 上游产物名保持不变：`libalkimia6.so`、`LibAlkimia6Config.cmake`
  （`Alkimia::alkimia` 目标）、`onlinequoteseditor6`、头文件目录 `include/alkimia/Qt6/alkimia/`
- 消费者入口：`find_package(LibAlkimia6 8.2.1 REQUIRED)` → `target_link_libraries(... Alkimia::alkimia)`

**配方来源说明（如实记录）**：本目录的 `conanfile.py` / `conandata.yml` /
`patches/0001-ohos-remove-ktextwidgets-dep.patch` 以仓库中已有的
`archives/a/alkimia/8.2.1`（上游名归档，已并入 main）的技术内容为基线，按上述
命名口径做**包名同步**（五点：`conanfile.name` / 归档目录 / test_package 的
`MANIFEST.yml` package 字段 / 文档串 / 测试输出串），并补充本轮独立验证证据
（本地 `conan create` 全量日志、真机 DAYU200 执行证据、下载路径崩溃复现记录）。

## 依赖矩阵（`conan install --build=never` 实测 28 包全部预编译解析成功）

| 依赖 | 版本 | 选型原因 |
|---|---|---|
| qtbase-sql-dbus | 6.11.1 | 提供 `Qt6::DBus`（基线 `qtbase/6.11.1` 无 DBus 组件，akonadi 25.12.3 先例） |
| qtdeclarative | 6.11.1 | `libqmlalkimia6.so` / qml 报价源插件 |
| gmp | 6.3.0.1 | `--enable-cxx` 提供 `gmpxx`（`AlkValue` 用 `mpq_class`） |
| knewstuff | 6.29.0.1 | 在线报价源仓库（KNS） |
| kcompletion / kiconthemes / kxmlgui / kconfigwidgets / kguiaddons / kcolorscheme / kitemviews / kconfig / kcoreaddons / ki18n / kcodecs / kwidgetsaddons | 6.18.0 | 上游 Qt6 分支 REQUIRED 的 KF6 组件 |
| ecm | 6.26.0 | `tool_requires`，ECM/`ecm_add_test(s)` |

依赖可用性预检：`conan list "libalkimia*" -r=ohpcd` → `Found 0 pkg/version recipes`
（W0 预检：包名未被占用，可安全新建包）。

## 关键适配点

1. `BUILD_WITH_QT6=ON`：上游用 `QtVersionOption` 模块选 Qt 版本，不显式打开会走
   Qt4/Qt5 分支报 `FindQt5` 失败。
2. `BUILD_APPLETS=OFF`（Plasma 未发布）、`ENABLE_FINANCEQUOTE=OFF`（需 perl）、
   `BUILD_TESTING=ON`（跑上游 autotests）。
3. `patches/0001-ohos-remove-ktextwidgets-dep.patch`：把 debug 日志窗口的
   `KTextEdit` 降级为 `QTextEdit`（`m_logWindow` 只用到 `setVisible/clear/append`
   三个 `QTextEdit` 原生 API，功能等价），并从 `find_package`/链接中移除
   `KF6TextWidgets`。原因：制品仓 `ktextwidgets` 只有 6.14.0（锁 KF 6.14 系），
   与 `knewstuff` 全系（锁 kconfig/6.18 系）版本冲突，无法共存。
4. GMP 查找：`FindGMP.cmake` 补 `gmpxx.h`/`libgmpxx`，配方侧把
   `GMP_INCLUDE_DIR`/`GMP_LIBRARIES` 指向 conan 包。
5. 可重定位链接（E537/R05，knewstuff 6.29.0.1 同款）：
   - 主库 `-Wl,-soname,libalkimia6.so`；
   - 已发布 KF6 包多数无 `DT_SONAME`，按裸 `-l` 基名链接 + PRIVATE
     `target_link_directories`；
   - `package()` 后 `_make_relocatable()` 用 `patchelf` 把绝对缓存路径/构建树
     相对路径的 `DT_NEEDED` 重写为裸 basename。
6. ctest 运行时垫片：已发布 kconfig/knewstuff 等包自带
   `../../bin/libKF6*.so` 相对 `DT_NEEDED`（它们构建树布局的遗留），OHOS musl
   按 cwd 解析路径型 NEEDED、不查 `LD_LIBRARY_PATH`；`_prepare_ctest_runtime_links()`
   在 `build/../bin` 建全部依赖库软链。
7. `TZ=UTC`：上游 `alkonlinequoteprivatetest` 的 `testParseQuoteJson` 喂
   UTC 日边界时间戳，非 UTC 时两条样本落到同一本地日期导致 map 退化为 1 条
   （上游时区依赖缺陷）。测试环境注入 `TZ=UTC` 后该用例 9/9 通过。

**补丁触及的上游测试相关文件（如实披露）**：除库源码与 `CMakeLists.txt` 外，
`patches/0001-ohos-remove-ktextwidgets-dep.patch` 还改动了两个**测试构建脚本**
（不涉及任何测试用例源码 `*.cpp/*.h`、不涉及断言与执行逻辑）：

- `autotests/CMakeLists.txt`：新增 `link_directories(${ALKIMIA_DEP_LIB_DIRS})`；
  测试目标 `LINK_LIBRARIES` 由 `${TEST_LIB} KF${QT_MAJOR_VERSION}::CoreAddons`
  改为 `${TEST_LIB}`（已发布 KF6 包无 `DT_SONAME`，须经裸 `-l` 基名链接，R05 可重定位）；
- `tests/CMakeLists.txt`：新增 `link_directories(${ALKIMIA_DEP_LIB_DIRS})`。

## 测试台账（数字均为本地实测）

### 上游测试（`ctest`，BUILD_TESTING=ON 默认形态）

上游 `autotests/CMakeLists.txt` 注册 **12** 个 CTest 目标。本轮 `conan create`
构建阶段实测执行 **9 个，9/9 通过**（`100% tests passed, 0 tests failed out of 9`）：

```
alkvaluetest / alkonlinequotesourcetest / alkquoteitemtest / alkcompanytest /
alkdomtest / alkexceptiontest / alkdateformattest /
alkonlinequoteprivatetest / alkwebpagetest
```

另有 **3 个网络型目标**由 `ctest -E`（配方内 `_run_upstream_tests()`）排除：

| 目标 | 排除原因 |
|---|---|
| `alkonlinequotestest` | 真实下载 `https://kmymoney.org/onlinequotestest.php`，离线沙箱无外网 |
| `alkdownloadengine-qt-test` | 真实 HTTP 下载（QtNetwork 后端） |
| `alknewstuffenginetest` | 访问 `https://autoconfig.kde.org/ocs/providers.xml` |

**本轮新增发现（如实记录，见 `reports/upstream-test-evidence.md`）**：为核对这些
网络型用例的技术原因，本轮额外用「内嵌 QTcpServer 报价服务 + 本地
`AlkOnlineQuote::launch`」构造了离线可复现的下载路径探针，结果该下载路径
（`AlkOnlineQuote::launch` → `AlkDownloadEngine::downloadUrlQt`）**稳定
SEGFAULT**（`si_addr=NULL`），且：

- 在 qemu-aarch64 仿真（`-L` 运行根）与 binfmt 透明执行下均复现；
- 在 **DAYU200 真机（OpenHarmony 6.0.0.47）** 上同样复现（`Signal 11`）；
- 换 `AlkOnlineQuotesProfile::Type::Test`（上游网络测试用的 profile 类型）同样复现；
- 上游 `alknewstuffenginetest` 本身在无网环境也会 SEGFAULT（既有配方笔记已记录）。

即：该下载路径在 OHOS musl 运行时下不可用，属既有环境/上游缺陷，与本轮适配
改动无关；因此消费者端到端用例不触发真实下载，只覆盖到「报价源解析失败」
这一不发起下载的错误契约（见下）。

未注册进 CTest 的上游目标（清点留痕，不计入 12）：`tests/` 下 4 个手工 GUI
冒烟可执行、webengine 变体（OHOS 无 QtWebEngine 制品）、`client-package`
（`ENABLE_CLIENT_PACKAGE_TEST=OFF`）、`appstreamtest`（无 `appstreamcli` 时不注册）。

### 消费者端到端（`test_package/test_libalkimia.cpp`，rule12）

经**安装产物**（`LibAlkimia6Config.cmake` → `Alkimia::alkimia`）走三条真实业务回环，
共 **23** 个校验点：

| 用例 | 内容 | 校验点 |
|---|---|---:|
| case1 金融金额计算回环 | 字符串解析（欧式逗号小数点）→ 复式记账四则运算 → `convertDenominator` 双向舍入 → `toString` 回环再解析 → `double` 构造 → 精度/分母换算 → 比较运算 | 12 |
| case2 报价源存储回环 | `AlkOnlineQuotesProfile` 持久化 `write` → 重开读取逐字段比对 → 消费者自建 CSV 源写读 → `rename` → `remove` 存储清空 | 8 |
| case3 报价引擎消费者契约 | `AlkOnlineQuote` 构造 + `setUseSingleQuoteSignal` 回读 + 未知报价源 `launch` 失败契约（返回 false、不发起下载） | 3 |
| 合计 | | **23** |

本轮实测：

- 本地 `conan create`（`ohos-aarch64-run`，qemu 执行 test_package）：
  `RESULT: 23 checks, 0 failures` / `ALL_CONSUMER_TESTS_PASSED`；
- DAYU200 真机（OpenHarmony 6.0.0.47 aarch64）：
  `RESULT: 23 checks, 0 failures`（证据 `reports/device-e2e-evidence.md` +
  `reports/device-e2e-_device_evidence.json`）。

### `conan create` 结果

`conan create` 退出码 0。产物：

- `lib/libalkimia6.so`（+ `.so.8` / `.so.8.2.1`）
- `lib/qml/...`（`libqmlalkimia6.so`）、`lib/qt6`、`lib/pkgconfig`
- `include/alkimia/Qt6/alkimia/` 16 个头文件
- `lib/cmake/LibAlkimia6-8.2/LibAlkimia6Config.cmake`（`Alkimia::` 命名空间）
- `bin/onlinequoteseditor6`（报价源编辑器 GUI 工具；`package_type = library` 的纯库包
  按 R38/PF8 不创建 commands.json，其 `--version/--help` 无输出属 GUI 工具正常行为，
  本地 CI 的 L2 冒烟据此 skip、非阻塞）
- `share/`（applications、icons、knsrcfiles、metainfo）

## 平台限制记录

- `/tmp` 只读（E002）：补丁生成等临时文件走 `$TMPDIR`。
- 网络：构建/测试环境无外网，3 个网络型上游用例经 `ctest -E` 排除；真实下载
  路径在 OHOS musl 运行时下 SEGFAULT（仿真与真机均复现，见上）。
- OHOS musl 动态加载器：路径型 `DT_NEEDED` 按 cwd 解析，不走 `LD_LIBRARY_PATH`
  （故需要 `_prepare_ctest_runtime_links()` 垫片与 `patch_elf` 归一化）。
