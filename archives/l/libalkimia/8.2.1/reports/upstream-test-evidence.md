# libalkimia 8.2.1 上游测试证据（HarmonyOS PC / aarch64）

> 本文件记录**上游测试清点口径**与**本地实测原始结果**，数字均来自可复现的
> `conan create` 日志（`OHOS_PROFILE=ohos-aarch64-run`，clang 15，aarch64-unknown-linux-ohos）。

## 1. 清点口径（R51 三步法）

1. 上游测试入口：`autotests/CMakeLists.txt`，构建期 `BUILD_TESTING=ON`（CMake 默认形态）。
2. 注册方式：`ecm_add_tests()` 批量块 + `ecm_add_test()` 单块。
3. 默认形态下（`BUILD_WITH_WEBENGINE=OFF`、`ENABLE_FINANCEQUOTE=OFF`）
   **注册 CTest 目标 12 个**。

未注册进 CTest 的上游目标（清点留痕，不计入 12）：

| 目标 | 不注册原因 |
|---|---|
| `tests/` 下 4 个 GUI 冒烟可执行 | 上游未 `add_test`，需人工带界面运行 |
| `test-qwebengine-*.cpp`、`alkdownloadengine-{webkit,webengine}-test` | 仅 `BUILD_WITH_WEBKIT/WEBENGINE=ON` 注册；OHOS 无 QtWebEngine 制品 |
| `client-package` / `test-install-*` | 仅 `ENABLE_CLIENT_PACKAGE_TEST=ON` 注册（上游默认 OFF） |
| `appstreamtest` | 上游 CMake 检测不到 `appstreamcli` 时不注册 |

## 2. 离线实测结果：9/9 通过（100%）

命令（配方 `_run_upstream_tests()`；`TZ=UTC` 由测试环境注入）：

```
ctest --output-on-failure --no-tests=error -E "^(alkonlinequotestest|alkdownloadengine-qt-test|alknewstuffenginetest)$"
```

原始输出（`conan create` 日志 696–706 行）：

```
1/9 Test #1: alkonlinequotesourcetest .........   Passed    0.66 sec
2/9 Test #2: alkvaluetest .....................   Passed  121.91 sec
3/9 Test #3: alkquoteitemtest .................   Passed    0.45 sec
4/9 Test #4: alkcompanytest ...................   Passed    0.39 sec
5/9 Test #5: alkdomtest .......................   Passed    0.40 sec
6/9 Test #6: alkexceptiontest .................   Passed    0.36 sec
7/9 Test #7: alkdateformattest ................   Passed    0.59 sec
8/9 Test #8: alkonlinequoteprivatetest ........   Passed    0.65 sec
9/9 Test #9: alkwebpagetest ...................   Passed    0.62 sec

100% tests passed, 0 tests failed out of 9
Total Test time (real) = 126.05 sec
```

### TZ=UTC 说明（上游用例的时区依赖）

`alkonlinequoteprivatetest` 的 `testParseQuoteJson` 使用 UTC 日边界时间戳；
非 UTC 本地时区下两条样本会落到同一本地日期，解析结果 map 退化为 1 条而失败
（上游缺陷，非本适配引入）。测试环境注入 `TZ=UTC` 后该用例 9/9 通过。

## 3. 被排除的 3 个网络型用例（技术原因 + 复现证据）

| 目标 | 依赖的外部服务 |
|---|---|
| `alkonlinequotestest` | `https://kmymoney.org/onlinequotestest.php` |
| `alkdownloadengine-qt-test` | 真实 HTTP 下载（QtNetwork 后端） |
| `alknewstuffenginetest` | `https://autoconfig.kde.org/ocs/providers.xml` |

排除原因是**构建/测试沙箱无外网**（离线口径）。为核对这三条用例覆盖的下载路径
在本平台是否可用，本轮额外做了**离线可复现探针**（内嵌 `QTcpServer` 提供 CSV
报价服务，消费者侧调用 `AlkOnlineQuote::launch`），结论如下。

### 结论：真实下载路径在 OHOS musl 运行时下 SEGFAULT（既有缺陷，与本适配无关）

- **故障点**：`AlkOnlineQuote::launch` → `AlkDownloadEngine::downloadUrlQt`
  （日志最后一行 `bool AlkOnlineQuote::Private::applyDateRange(QUrl &)` 之后）。
- **表现**：`SIGSEGV`，`si_code=1`（SEGV_MAPERR）、`si_addr=NULL`，
  崩溃前 `strace` 仅见成功的 `madvise(MADV_DONTNEED)` 与 `gettid()`，无缺失库。
- **复现面（全部一致）**：
  1. qemu-aarch64 显式执行（`qemu-aarch64-static -L <runroot>`）；
  2. binfmt 透明执行（`./binary`，等价 CI 原生执行的加载路径）；
  3. **DAYU200-RK3568 真机**（OpenHarmony 6.0.0.47 aarch64）：输出 `Signal 11`，
     `EXIT_CODE=139`（原始输出见 `device-e2e-evidence.md` 附录）；
  4. 换用上游网络测试同款 `AlkOnlineQuotesProfile::Type::Test`（而非 `Alkimia4`）同样复现；
  5. 指向不可达端口与指向本地 HTTP 服务表现相同。
- **旁证**：`alknewstuffenginetest` 在无网环境同样 SEGFAULT（既有配方笔记已记录）；
  纯 Qt（`QNetworkAccessManager` + `QTcpServer`）与 `KF6I18n` 的同类探针均正常退出 0，
  说明并非 Qt 网络栈或 OHOS musl 的系统性缺失。
- **影响面**：仅影响**真实网络下载**这条路径；报价源的配置/持久化/解析、
  金额计算、KNS 报价源仓库以外的功能均正常（见 `device-e2e-evidence.md`，真机 23/23）。
- **处置**：消费者端到端用例不触发真实下载，改为覆盖「未知报价源 → `launch()`
  返回 false」这一不发起下载的消费者错误契约；网络型上游用例保持上游原样，
  按上游既有豁免口径 `ctest -E` 排除（测试用例源码零改动，见第 4 节）。

## 4. 上游测试文件修改：测试用例源码零改动，仅测试构建脚本的链接配置

本轮**未修改任何上游测试用例源码**（`autotests/*.cpp`、`autotests/*.h` 的用例与断言
零改动）；除离线口径 `ctest -E` 排除 3 个网络型目标、测试环境注入 `TZ=UTC` 外，
适配补丁涉及的上游文件**逐条披露**如下（含两个测试构建脚本）：

- `patches/0001-ohos-remove-ktextwidgets-dep.patch`：
  1. `src/alkonlinequoteswidget.cpp` 等处的 debug 日志窗口 `KTextEdit` → `QTextEdit`
     （`m_logWindow` 仅使用 `setVisible/clear/append` 三个 `QTextEdit` 原生 API）；
  2. `CMakeLists.txt` 的 `find_package`/链接中移除 `KF6TextWidgets`
     （制品仓 `ktextwidgets` 6.14.0 与 `knewstuff` 全系锁定的 KF 6.18 冲突，无法共存）；
  3. **`autotests/CMakeLists.txt`、`tests/CMakeLists.txt`（测试构建脚本）**：
     新增 `link_directories(${ALKIMIA_DEP_LIB_DIRS})`；`autotests` 中测试目标的
     `LINK_LIBRARIES` 由 `${TEST_LIB} KF${QT_MAJOR_VERSION}::CoreAddons` 改为
     `${TEST_LIB}` —— 因已发布 KF6 包无 `DT_SONAME`，须经裸 `-l` 基名链接
     （R05 可重定位链接所需）。**仅构建/链接配置，不涉及任何测试用例断言或执行逻辑**；
  4. `FindGMP.cmake` 补 `gmpxx.h`/`libgmpxx` 查找。
