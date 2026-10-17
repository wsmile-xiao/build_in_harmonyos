# nzbget 26.2 — 适配笔记与上游测试范围说明

## 库信息
- 软件：nzbget（Usenet 二进制下载器）
- 上游：https://github.com/nzbgetcom/nzbget（v26.2，tar.gz sha256 `8642dda8…319d`，本地实测与 conandata 一致）
- 构建：CMake；依赖 libxml2/2.15.3、openssl/3.5.6、zlib/1.3.1、boost/1.84.0（Conan）
- 产物：`bin/nzbget`（aarch64 ELF，stripped，已 OHOS 签名）

## OHOS 适配要点
1. Conan target 命名映射：`OpenSSL::SSL/Crypto` → `openssl::openssl`；`ZLIB::ZLIB` → `zlib::zlib`。
2. Boost：改用 Conan Boost 头；Boost.JSON header-only（`BoostJsonImpl.cpp` 内 `#include <boost/json/src.hpp>`）；
   上游 `ExternalProject` 在线 clone（rapidyenc / par2-turbo）改为本地解包（codeload 归档）以适配 worker 网络。
3. `pthread_setcancelstate` 在 OHOS 缺失 → 定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（Boost sp_thread_sleep 走 nanosleep 回退）。
4. 打包后对 `bin/nzbget` 做 OHOS ELF 签名（binary-sign-tool + 0755）。

## 上游测试（9 个 CTest 项）与本次执行范围（权威取证）

上游 `tests/CMakeLists.txt`：
- 第 1 行 `find_package(Boost COMPONENTS unit_test_framework REQUIRED)`
- 第 43-51 行：9 个 `add_test()`（UtilTest、FeedTest、QueueTest、MainTest、ExtensionTest、
  NNTPTest、SystemTest、PostprocessTest、SystemHealthTest），**共享同一 `nzbget_tests`
  Boost.Test 可执行文件**，用 `--run_test=<suite>` 选择套件。

**2026-09-12 更新：上游测试已真机实际执行。** 下表为历史记录（当时的 NOT_RUN 分析），
已被下面的实测结果取代。

**本次 recipe 明确 `ENABLE_TESTS=OFF`，9 项均 NOT_RUN（0/9 executed）**；原因是可复核的环境/范围限制，
而非"平台绝对不可做"：

| # | CTest 项 | 未执行/无法通过的技术原因 | 证据 |
|---|----------|---------------------------|------|
| 1 | UtilTest | 依赖 `Boost::unit_test_framework`；套件内 Unpack 用例调用外部 **7z/par2/unrar** | `tests/util/Unpack.cpp`（7z/par2/unrar 调用）；设备 `command -v 7z par2` = MISSING |
| 2 | FeedTest | 依赖 `Boost::unit_test_framework`（nzb/XML 解析用例，无独立外部服务） | `tests/CMakeLists.txt:1`；设备 conan boost 包无 `libboost_unit_test_framework` |
| 3 | QueueTest | 同上；用例引用 par2/7z 路径 | `tests/queue/*.cpp`；设备 7z/par2 MISSING |
| 4 | MainTest | 同上；命令行/选项用例引用 unrar/7z | `tests/main/*.cpp`（unrar/7z）；设备 7z MISSING（unrar 存在） |
| 5 | ExtensionTest | 同上；需加载扩展脚本 + loopback socket | `tests/extension/*.cpp`（socket） |
| 6 | NNTPTest | 同上；需本地 mock NNTP 服务（socket bind/listen） | `tests/nntp/{ServerPool,Decoder}.cpp`；worker 网络受限 |
| 7 | SystemTest | 同上；系统信息/守护进程生命周期相关系统路径 | `tests/system/SystemInfo.cpp` |
| 8 | PostprocessTest | 同上；ParChecker/RarReader/DirectUnpack 调用 **par2/unrar** | `tests/postprocess/{ParChecker,RarReader,DirectUnpack}.cpp`；设备 par2 MISSING |
| 9 | SystemHealthTest | 同上；NewsServerValidator 需**真实 NNTP 服务器**，另有路径/扩展脚本校验 | `tests/systemhealth/NewsServerValidator.cpp` 等 |

补充说明（可复核命令，真机 HarmonyOS PC）：
```
command -v 7z 7za 7zr par2 par2cmdline   # → 全部 MISSING（unrar 存在）
ls <conan>/p/*/p/lib/libboost_unit_test_framework*   # → 无（boost 包未构建该库）
```
因此：9 项共享的 `nzbget_tests` 无法在当前 Conan Boost 资源下链接，且其中 Unpack/Postprocess 用例
即使能编译也依赖设备上不存在的 7z/par2 与真实 NNTP 服务。**未做任何测试裁剪，也未虚报通过率。**

## 真实消费者验证（真机执行，1/1 PASS）
- `nzbget --version`：执行打包后的 aarch64 二进制并校验版本 banner → PASS（`test_package/`）。

## 后续可选（超出本次最小适配范围）
若评审要求纳入上游 9 项：需（a）为 recipe 增加 `ENABLE_TESTS=ON` 分支并链接
`Boost::unit_test_framework`（Conan boost 需开启 unit_test 组件或 `tool_requires` 提供）；
（b）在 CI worker 提供 7z/par2 与可用的 loopback NNTP mock；（c）逐项记录 OHOS 运行结果。

---

# 上游测试真机实际执行结果（2026-09-12，取代以上 NOT_RUN 分析）

上文那些"因缺依赖/缺服务而不执行"的判断**已被实测推翻**。真正需要解决的自始至终只有
一个依赖问题（Boost.Test），其余 suite 并不需要外部服务。

## 依赖：boost/1.84.0 → boost/1.90.0

`boost/1.84.0` 不提供 Boost.Test（其配方第 124 行自述"本配方未编译"）。
仓库已有 `boost/1.90.0`（docstring："header-only + Boost.Test static library"），
实测其包内具备：`include/boost/json/src.hpp`、`include/boost/test/included/unit_test.hpp`、
`include/boost/test/impl/`（21 个 .ipp）、`lib/libboost_unit_test_framework.a`，
且 CMakeDeps 导出组件 `Boost::unit_test_framework`（已实测可被
`find_package(Boost COMPONENTS unit_test_framework REQUIRED)` 解析）。
不选 `boost/1.90.0.4.1`：它有 unit_test_framework，但 headers 被裁剪到 204 项且**不含 `boost/json`**。

另注：`tests/main.cpp` 用的是 `#include <boost/test/included/unit_test.hpp>`
（Boost.Test 单 TU header-only 模式），测试二进制**并不链接** `libboost_unit_test_framework`；
`tests/CMakeLists.txt:1` 的 `find_package(... REQUIRED)` 是 configure 期门禁。

## 恢复上游 std::filesystem 路径（删除多余的 Boost::filesystem）

上游 `cmake/posix.cmake:24-27`（及 115-117）只在 `NOT HAVE_STD_FILESYSTEM` 时才要
`Boost::filesystem`；`HAVE_STD_FILESYSTEM` 由 `cmake/common.cmake:59-70` 的真实编译测试决定。
用 OHOS clang 15.0.4（aarch64-unknown-linux-ohos, -std=c++17 -stdlib=libc++ + SDK sysroot）
对**上游原文片段**做 compile+link：**rc=0 → OHOS 上 HAVE_STD_FILESYSTEM=TRUE**。
故原先配方里
`find_package(Boost COMPONENTS filesystem REQUIRED)` + `Boost::filesystem`
是我们自己加的 workaround，已删除；改为链接 header-only 的 `Boost::boost`
（Boost.JSON 是 header-only，由 `daemon/util/BoostJsonImpl.cpp` 编进工程）。

## configure 期门禁：CMAKE_POLICY_DEFAULT_CMP0167=NEW

nzbget 顶层 `cmake_minimum_required(VERSION 3.13)` → CMP0167 为 OLD → CMake 走
`FindBoost` 模块，而 FindBoost 自行做组件校验，对 Conan Boost 报
`missing: unit_test_framework`；因 `tests/CMakeLists.txt:1` 是 REQUIRED，configure 直接失败。
设 `CMAKE_POLICY_DEFAULT_CMP0167=NEW` 后改用 CMakeDeps 生成的 `BoostConfig.cmake`，问题消失。

## 运行期：LD_LIBRARY_PATH

`nzbget_tests` 链接共享依赖（libxml2 等），而 CMake 对 HarmonyOS 没有平台模块、
不生成 RPATH，直接执行会：
```
Error loading shared library libxml2.so.16
Error relocating ...: xmlNewNode: symbol not found
```
build() 内执行测试时把各依赖的 `cpp_info.libdirs` 汇入 `LD_LIBRARY_PATH` 即可。
（同一根因在 nextpnr 的 build 期生成器上也出现过。）

## 实测结果（HarmonyOS PC，aarch64，OHOS 6.0，Clang 15.0.4）

命令：`ctest -N` → `nzbget_tests --list_content` → `ctest --output-on-failure --timeout 120`

| CTest suite | 实际执行 case 数 | 结果 | 耗时 |
|---|---|---|---|
| UtilTest | 31 | PASS | 0.06 s |
| FeedTest | 11 | PASS | 0.07 s |
| QueueTest | 3 | PASS | 0.06 s |
| MainTest | 12 | PASS | 0.06 s |
| ExtensionTest | 8 | PASS | 0.06 s |
| NNTPTest | 17 | PASS | 0.05 s |
| SystemTest | 1 | PASS | 24.53 s |
| PostprocessTest | 36 | PASS | 0.67 s |
| SystemHealthTest | 42 | **FAIL（2 case）** | 0.13 s |

- CTest suite：**9 项，8 passed / 1 failed**（`89% tests passed`）
- Boost.Test test case：`--list_content` 列出 **167** 项；按 suite 实际执行 **161** 项
- **PASS 159 / FAIL 2 / SKIP 0 / NOT_RUN 0**

注意 **NNTPTest（17 case）、PostprocessTest（36 case）、ExtensionTest（8 case）全部通过** ——
它们并不需要真实 NNTP 服务或 par2/7z 二进制；此前"因缺服务整体不执行"的判断不成立。

## 2 个失败 case 的真实原因（非缺依赖）

```
tests/systemhealth/Validators.cpp(255): error: in
  "SystemHealthTest/FilesystemValidatorsSuite/TestDirectoryWritable":
  check SystemHealth::Directory::Writable(d).IsError() has failed
tests/systemhealth/Validators.cpp(271): error: in
  "SystemHealthTest/FilesystemValidatorsSuite/TestDirectoryReadable":
  check SystemHealth::Directory::Readable(d).IsError() has failed
```

源码 `tests/systemhealth/Validators.cpp:246-274`：
```cpp
fs::permissions(d, fs::perms::owner_write, fs::perm_options::remove);
BOOST_CHECK(SystemHealth::Directory::Writable(d).IsError());
```
用例先 `create_directory`，再**去掉 owner 的写/读权限位**，然后断言该目录被判定为不可写/不可读。

**根因：HarmonyOS/HMDFS 不按 POSIX owner 权限位限制属主对其自身目录树的访问。**
去掉位之后目录仍然可写/可读，`IsError()` 返回 false，断言失败。
这是平台文件系统语义差异，不是缺依赖、也不是本次改动引入的缺陷。

值得注意：这两段检查被 `#ifdef HAVE_STD_FILESYSTEM` 包住，**只有在 std::filesystem 路径生效时
才会编译进去** —— 也就是说，只有当我们按上文恢复了上游的 std::filesystem 路径后，
这两个 case 才真正被执行（此前 Boost.Filesystem 路径下它们根本不会被编译）。
