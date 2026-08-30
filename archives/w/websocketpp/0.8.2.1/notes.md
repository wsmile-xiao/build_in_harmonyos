# websocketpp 0.8.2.1 适配笔记

> 定位：这是 `archives/w/websocketpp/0.8.2`（PR #7052，已 CI 绿）的**适配修订**（R37），
> 不是新版本上游。上游源码仍是 0.8.2 tag，**打包产物（头树 + 补丁 0001-0003）与 0.8.2 逐字节相同**。
> 与 0.8.2 的实质差别有两点：① boost 变体 pin 到 `boost/1.90.0.4`；② 按 PR #7144 评审意见
> 把**上游官方测试真正接入构建**（layer 1：`build()` 内 CMake harness + ctest，31 个测试二进制全绿）。
> **补丁设计、伪发布史、asio 五类断口的完整表格**
> 都在 `archives/w/websocketpp/0.8.2/notes.md`（单一真相源，本文件不重复抄一遍），
> 这里记录"为什么要多一个版本""换 boost 变体后重新验证的结果""上游测试是怎么跑起来的"。

## 编译环境
- 构建系统: custom（header-only：`package()` 直接 copy 头树，不调用上游构建系统；
  `build()` 只为本仓库自研的 `upstream_tests/CMakeLists.txt` 测试 harness 服务，产物不参与打包）
- 编译日期: 2026-08-28（配方与补丁 0001-0003）／2026-08-30（上游测试接入，补丁 0004/0005 + harness）
- 编译器: clang/clang++ 15.0.4，`aarch64-unknown-linux-ohos`（HarmonyOS HongMeng Kernel 1.12.0）
- 包管理: Conan 2.29.1（支持 `os=OHOS`），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 为什么需要 0.8.2.1（理由一：boost 变体）

下游积分赛任务 **autobahn-cpp 17.5.1-git7cc5d37** 的 `CMakeLists.txt:33` 是

```cmake
find_package(Boost REQUIRED COMPONENTS program_options system thread random)
```

设备端把本仓库所有 boost 变体的**实际包内容**查了一遍（不是看配方怎么写，是看包目录里有什么）：

| 变体 | `include/boost/asio` | 包内 `.a` | 声明组件 |
|---|---|---|---|
| `boost/1.90.0`（0.8.2 现 pin） | YES | 仅 `unit_test_framework` | `boost`(headers) + `unit_test_framework` |
| `boost/1.90.0.4` | YES | 12 个，含 **`libboost_thread.a`、`libboost_program_options.a`** | 含 `system`、`thread`、`program_options` |
| `boost/1.91.0.1.1` / `1.91.0.1` / `1.91.0` | **NO（include 树里没有 boost/asio）** | 含 `random` | 含 `random`、`thread` |

- autobahn 库代码真实用到 `boost::promise`/`boost::future`（`autobahn/boost_config.hpp` include
  `boost/thread/future.hpp`，`wamp_call.ipp`、三个 transport 里都在用）→ 需要**已编译的 Boost.Thread**；
- autobahn 的 examples 用 `boost/program_options` → 需要 `libboost_program_options.a`；
- 而 websocketpp 必须要 asio 头 → 1.91.x 系列出局（包里根本没有 asio）。

结论：**只有 `boost/1.90.0.4` 同时满足 asio 头 + thread + program_options**。
而同一张 Conan 依赖图里 boost 只能有一个版本：autobahn 若 require `boost/1.90.0.4`，
它依赖的 `websocketpp/0.8.2` 钉着 `boost/1.90.0` 就必然 version conflict。
不去回改已提交的 0.8.2（它已经过审计与 CI 验证，改 pin 会让那份证据失效），
按 R37 用版本号后缀开 `0.8.2.1` 对齐 —— 这是本版本存在的**理由一**（理由二：上游测试接入，见 §上游测试）。

（`random` 这一项：全仓库 grep `boost/random`、`mt19937`、`uniform_` **零命中**，
是上游 CMake 的过度声明，归 autobahn 自己的补丁处理，不影响本版本选型。）

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build websocketpp 0.8.2.1 \
  --url=https://github.com/zaphoyd/websocketpp/archive/refs/tags/0.8.2.tar.gz
# 独立 .work/.orig + 独立编辑追踪器（不复用 0.8.2 的，避免 finish 的补丁追踪串台）
patch -p1 < 0.8.2/patches/0001-... 等三个补丁       # 应用到 0.8.2.1 的 .work
python3 scripts/ohc-run.py refresh-patch websocketpp 0.8.2.1 --auto   # 重生成补丁
python3 scripts/ohc-run.py conan-verify websocketpp 0.8.2.1
python3 scripts/ohc-run.py finish websocketpp 0.8.2.1 built
```
与 0.8.2 的配方差别：`version = "0.8.2.1"`、`self.requires("boost/1.90.0.4")`，
外加**上游测试接入**所需的 `generate()`（CMakeToolchain/CMakeDeps）、`build()`（打补丁 + harness + ctest）、
`export_sources()`（多导出 `upstream_tests/*`）和 `conandata.yml` 里新增的 0004/0005 两条。
`package()` / `package_info()` 与 0.8.2 相同，**打包产物不变**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 换 boost 变体后，兼容层是否还走现代分支（会不会静默退回旧 API 路径） | 门控条件写的是 `BOOST_ASIO_VERSION>=103100`，与 boost 包变体无关 | 实测 `boost/1.90.0.4` 包里 `BOOST_ASIO_VERSION = 103800`（Asio 1.38）→ 仍走现代分支；补丁原样应用（`conan-create.log` L102-104 三条 `Apply patch`），无需任何改动 |
| 2 | 担心 `boost/1.90.0.4` 把 openssl 带进来或与之冲突 | 该配方**没有任何 `self.requires`**（grep 确认），不传递 openssl | 保持与 0.8.2 相同的显式 `requires("openssl/3.5.6")`（`config/asio*.hpp` → `boost/asio/ssl.hpp` → `openssl/*.h`） |
| 3 | `conan create` 会不会现场编译 boost（可能几十分钟且超 W3 预算） | 需要确认制品仓有匹配 profile 的二进制包 | 用 R35 允许的 `conan install --requires=boost/1.90.0.4`（**不是** `conan list`）实测：packageID `22b8e4fc1cb15b5734a6aac98d42c2eeee4d41eb`、recipe rev `bbbd49a1e113…` 已在缓存，"Already installed" → 无源码编译 |
| 4 | 归档骨架里 `status: published`、`build_system: "{BUILD_SYSTEM}"`、`sha256: ""`、`build.system: autotools` 全是占位 | init-build 的模板默认值 | 按实测改写；状态先 `pending_ci`，由 `finish` 升级为 `built`（不手写 `published`） |
| 5 | 绕过 SCons 直接编译 `test/*.cpp` 时无法链接出可执行文件（33 个用例都没有 main） | 用例用现代入口 `BOOST_TEST_MODULE` + `<boost/test/unit_test.hpp>`，该入口**需要已编译的 `libboost_unit_test_framework`**；而本版本 pin 的 `boost/1.90.0.4` 包（设备端 `conan cache path boost/1.90.0.4:22b8e4fc…` → `…/boost8a980d0b4e49b/p`）里 12 个 `.a` 恰好**没有**这一个（含它的是 `boost/1.90.0` 那档，但那一档只有 `libboost_unit_test_framework.a`，没有本版本要提供的 thread/program_options，二者又不能在一张依赖图里共存） | 补丁 0004：改用 header-only 的 `<boost/test/included/unit_test.hpp>`（自带 main，只吃头文件），彻底不依赖 Boost.Test 编译库。**注意：0.8.2 的 MANIFEST 把这条原因写成"上游用例用旧入口 `init_unit_test_suite`"，实测不成立**——`grep -rn init_unit_test_suite test/` 在源码里零命中（唯一命中是上游误提交的二进制 `test/http/test.out`） |
| 6 | `endpoint.cpp` / `integration.cpp` / `asio/timers.cpp` 编译报 `no member named 'io_service' / 'from_string' / 'query' / 'deadline_timer'` | Boost.Asio ≥1.31 删掉这些旧 API；与库里 0001-0003 面对的是同一批断口，只是测试源码没被那三个补丁覆盖 | 补丁 0005 做等价迁移（`io_context`、`make_address`、resolver results、`steady_timer` + `std::chrono`）；只改 3 个测试文件，不动库头 |
| 7 | harness 里 `find_package(OpenSSL)` 在 Conan CMakeDeps 下不可靠（生成的 config 是小写 `openssl`，因为 openssl/3.5.6 配方没设 `cmake_file_name`） | 依赖方属性缺失，不是本平台问题（ixwebsocket 曾为此直接改调用名） | 配方用 `self.dependencies[...].cpp_info.aggregated_components()` 把 boost/openssl 的绝对路径作为 cache 变量注入 harness，harness 只做 `find_library(... HINTS ... REQUIRED)`，绕开命名层 |
| 8 | 3 个 permessage-deflate 用例链接报 `undefined symbol: deflate/inflate`；且标准 `find_package(ZLIB)` 在设备上报 `Could NOT find ZLIB` | 之前"本环境没有 zlib"的判断是**错的**：OHOS SDK sysroot 有 `usr/include/zlib.h` 与 `usr/lib/aarch64-linux-ohos/libz.so`，只是 CMake 的平台探测不认识 HarmonyOS | harness 增加 `CMAKE_CXX_IMPLICIT_INCLUDE/LINK_DIRECTORIES` 兜底 + `ZLIB::ZLIB` imported target；找到则编 31 个（含 3 个 zlib 用例），否则降级为 28 个并 `message(WARNING)`。设备实测走"找到"分支，3 个 zlib 用例全部注册并通过 |
| 9 | 首次**端到端** `conan create` 在 `build()` 里失败：`CMake Error: The source directory ".../b/webso60688610d0ef4/b/upstream_tests" does not appear to contain CMakeLists.txt`（G2 FAIL） | `export_sources()` 里写成 `copy(self, "upstream_tests/*", src=self.recipe_folder, ...)`，`copy` 默认 `keep_path=True` 会保留相对路径 → 缓存里成了 `es/upstream_tests/upstream_tests/CMakeLists.txt` 双层目录（设备实测 `ls -la .../b/upstream_tests`） | 改为从目录本身取文件：`copy(self, "*", src=os.path.join(self.recipe_folder, "upstream_tests"), dst=os.path.join(self.export_sources_folder, "upstream_tests"))`。这条也是"独立 harness 跑通 ≠ layer-1 跑通"的实证：导出/布局问题只有在真实 `conan create` 里才暴露，所以必须补轮次 C |
| 10 | 31/31 已经在跑，但 `conan create` 日志里 `grep ctest` **零命中**，评审与 L1c 都拿不到"跑的是哪条命令"的证据 | `cmake.test()` 驱动的是 CMake 的 `test` 构建目标，日志只有一行 `Running CMake.build(target="test")`，ctest 命令本身不出现；且按 conan-io/conan#12407 它默认不转发 `--output-on-failure`，失败用例的诊断也会被 CTest 吞掉 | 改成 `self.run("ctest --output-on-failure", cwd=self.build_folder)`（本仓库 spectra/geos/nss-wrapper 同样写法），日志出现 `RUN: ctest --output-on-failure`（轮次 D L1088）。另按本仓库 240 个配方的既有约定补一行 `HMBS_UPSTREAM_TEST_RESULT=<json>`，数字解析自 ctest 汇总行（解析不到时如实给 0，不伪造通过），让规则 4 的通过率可直接机读 |

## 源码修改

补丁 0001-0003 与 0.8.2 **逐字节相同**（`cmp` 已验证；sha256 与 `conandata.yml` 登记值一致）；
0004/0005 是本版本新增，**只作用于 `test/` 目录**，不触碰被打包的 `websocketpp/` 头文件树：

| 补丁 | 内容 | sha256（前 12） |
|---|---|---|
| `0001-websocketpp-common-asio.hpp.patch` | 版本门控兼容层：`io_service`→`io_context` 别名、`work`→`executor_work_guard`、`is_expired()` 取代被删的 `expires_from_now()` getter、free `post()`/`restart()` 包装、resolver 包装（`query`/`iterator`→`results_type`） | `290579891a8c` |
| `0002-websocketpp-transport-asio-connection.hpp.patch` | 调用点改走 `is_expired()` / `post_handler()` | `022f9de81560` |
| `0003-websocketpp-transport-asio-endpoint.hpp.patch` | work guard 构造、`max_listen_connections`、`reset()`→包装、`listen()/async_resolve()/handle_resolve()` 用 resolver results | `5bc89dd35ff6` |
| `0004-test-boost-test-header-only.patch` | 33 个 `test/**/*.cpp`：`<boost/test/unit_test.hpp>` → `<boost/test/included/unit_test.hpp>`（header-only，自带 main），因为本仓库 boost 包不提供 `libboost_unit_test_framework` | `c1b3349ead79` |
| `0005-test-asio-modern-api.patch` | 3 个测试文件的 Boost.Asio ≥1.31 迁移：`endpoint.cpp`（`io_service`→`io_context`、`address::from_string`→`make_address`）、`integration.cpp`（另加 resolver `query`/`iterator`→`results_type`、`posix_time::seconds`→`std::chrono::seconds`）、`asio/timers.cpp`（`deadline_timer`→`steady_timer`、补 `<chrono>`） | `c88cbac0267a` |

设计依据（为什么按 Asio 版本门控而不是 `__OHOS__`、为什么只留一处 `#if`、可上游性论证）见
`archives/w/websocketpp/0.8.2/notes.md` §3；同一套论证已在本版本被**跨 boost 变体复用成功**，
这是对 `DRAFT-asio-classic-executor-boost-1-88.kv` 那条知识的第二次验证。

## 依赖版本

- `boost/1.90.0.4`（recipe rev `bbbd49a1e113fdc339cf435deb11a635`；`BOOST_VERSION 109000`、
  `BOOST_ASIO_VERSION 103800`；包内含 asio 头 + `libboost_thread.a` / `libboost_program_options.a` 等 12 个 `.a`）
- `openssl/3.5.6`
- 二者均用 `conan download <ref> -r ohpcd --only-recipe` / `conan install --requires=` 实测已发布（R35/R36）

## 验证结果

### 轮次 A：boost 变体切换（2026-08-28，尚无上游测试接入）

```bash
$ python3 scripts/ohc-run.py refresh-patch websocketpp 0.8.2.1 --auto
  变更文件 (3): common/asio.hpp, transport/asio/connection.hpp, transport/asio/endpoint.hpp
  生成 3 个补丁；与 0.8.2 同名补丁 cmp → SAME / SAME / SAME
$ python3 scripts/ohc-run.py conan-verify websocketpp 0.8.2.1
  G0 G1 G2 G3 G4 L2 L4 L5  →  全部 ✅ PASS（配方验证通过）
$ grep -nE "Apply patch|all checks passed" reports/conan-create.log
  L102-104 Apply patch (portability) ×3
  L198 Running test() → L200 test_websocketpp: all checks passed
$ grep -oE "boost/1\.90\.0\.[0-9]+" reports/conan-create.log | sort -u
  boost/1.90.0.4          # 依赖组合确实是新 pin，且二进制包命中缓存未现编
$ 稳定性：功能测试（38 断言真实 WebSocket 回环会话）与 0.8.2 同一份源码，
  0.8.2 侧已连续 5 次 rc=0（单次 ~27 ms）
```

`test_package/` 四个文件与 0.8.2 同源（只把注释/`package:` 字段里的版本号改成 0.8.2.1）：
18 个单元断言 + 20 个会话断言 = **38**，与 `test_package/MANIFEST.yml` 的 `assertion_count` 一致。

### 轮次 B：上游测试接入（2026-08-30，设备端）

```bash
# 1) 补丁可应用性（在设备端独立 .work 副本上）
$ patch -p1 --dry-run < 0001..0005        # 5/5 干净应用
# 2) harness 独立构建 + 执行（$HOME/tmp/wspp-harness-build，cmake 4.1.2 + 设备 clang 15）
$ ctest --output-on-failure
  100% tests passed, 0 tests failed out of 31
  Total Test time (real) = 17.36 sec
$ 逐个二进制 --report_level=detailed
  31 binaries / 316 test cases / 1590 assertions / 0 non-zero rc
```

- 补丁 0001-0003 仍与 0.8.2 逐字节相同；0004/0005 只改 `test/`，`shasum -a 256` 与
  `conandata.yml` 登记值一致（`c1b3349ead79…` / `c88cbac0267a…`）。

### 轮次 C：端到端 `conan create`（2026-08-30，设备端，与 CI 同源入口）

第一次在提交 `e02b3febd3` 上跑 **G2 FAIL**（§遇到的问题 第 9 条：`export_sources` 双层目录），
修复提交 `71a906e499` 后重跑通过：

```bash
$ python3 scripts/ohc-run.py conan-verify websocketpp 0.8.2.1
  G0 G1 G2 G3 G4 L2 L4 L5  →  ✅ 配方验证通过
$ grep -nE "Apply patch|Running test\(\)|all checks passed" archives/w/websocketpp/0.8.2.1/reports/conan-create.log
  L111-115 Apply patch (portability) ×5          # 0001-0003（库）+ 0004/0005（test）
  L1091    Test project .../b                       # build() 内 harness
  L1155    100% tests passed, 0 tests failed out of 31
  L1157    Total Test time (real) =  17.37 sec
  L1252    (test package): Running test()
  L1254    test_websocketpp: all checks passed
$ find <package> -type f ! -name '*.hpp'      # 打包面未被测试污染
  licenses/COPYING  conaninfo.txt  conanmanifest.txt      # 93 个头文件，test/ 零泄漏
```

即：**上游 layer-1 测试已在真实 `conan create` 内通过 31/31，且 `test_package` 同批通过**；
`reports/conan-create.log` 被 `.gitignore` 覆盖（不入库），关键行已抄录在此。
设备端验证到此闭环；**仍待完成的是远端 CI 绿灯与评审**（设备验证 ≠ CI 验证）。

### 轮次 D：改直接调用 ctest + 补机器可读结果行（2026-08-30，提交 `852482425e`）

轮次 C 的日志里**找不到字面 `ctest`**（`cmake.test()` 走 CMake 的 `test` 目标，日志只有
`cmake --build . --target test`），评审与 L1c 都看不到执行的是哪条命令。改为
`self.run("ctest --output-on-failure", cwd=self.build_folder)`，并按本仓库既有约定在其后打印
一行 `HMBS_UPSTREAM_TEST_RESULT=<json>`（数字解析自 ctest 汇总行）。同一入口重跑（先
`conan remove "websocketpp/0.8.2.1*" -c` 保证干净构建）：

```bash
$ python3 scripts/ohc-run.py conan-verify websocketpp 0.8.2.1   # G0 G1 G2 G3 G4 L2 L4 L5 全绿
$ grep -nE "RUN: ctest|tests passed|HMBS_UPSTREAM|all checks passed" archives/w/websocketpp/0.8.2.1/reports/conan-create.log
  L1088  RUN: ctest --output-on-failure                              # 命令本身进日志
  L1153  100% tests passed, 0 tests failed out of 31
  L1155  Total Test time (real) =  17.48 sec
  L1157  HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "ctest",
         "command": "ctest --test-dir .../b/webso19864c96130f3/b --output-on-failure",
         "discovered": 31, "executed": 31, "passed": 31, "failed": 0, "skipped": 0}
  L111-115 Apply patch (portability) ×5                              # 0001-0003 + 0004/0005
  L1251  (test package): Running test()
  L1253  test_websocketpp: all checks passed
$ find <package> -type f | grep -v '\.hpp$'   # 93 个头文件 + licenses/COPYING + conan{info,manifest}.txt
$ find <package> -path "*test*" | wc -l       # 0，test/ 零泄漏
```

标记行是 `_emit_hmbs_upstream_marker()` 再跑一次 ctest 解析出来的，因此套件在 `build()` 内实际执行两遍
（17.5s × 2）。这是为了让规则 4 能直接取到 `discovered/passed/failed` 的确定数字而接受的代价。

## 上游测试

> 本节是 PR #7144 评审意见（Septest，VERDICT=FAIL 规则 4：上游测试通过率 0/35）的直接产出。
> 0.8.2 那份"上游测试跑不了"的声明里，第 3 条理由（旧入口 `init_unit_test_suite`）**经复核不成立**，
> 已在下方"更正"里说明；其余两条成立。本版本不再以"跑不了"结案，而是把上游官方测试跑起来了。

### 1. 上游自己的 SCons 路径为什么不能用（保留成立的两条实证）

1. `SConstruct` 是 Python 2 专用：L31/L35/L178 用 `os.environ.has_key()`，设备端 Python 3.12.8 直接
   `AttributeError`；且 `command -v scons` 在设备与 CI 环境均无输出（scons 未安装，pip 也不在 CI 里装）。
2. `SConstruct` L35/L176-180 要求 `BOOST_ROOT` 或 `BOOST_INCLUDES`+`BOOST_LIBS` 指向 boost 的
   `stage/lib` 预编译树；本仓库 boost 由 Conan 提供，没有 stage 树这个布局。
3. `env.Object('uri_boost.o', ["uri.cpp"])` 这类规则还依赖 SCons 自己的 variant_dir 复用逻辑，
   照抄等于重写一遍构建系统。

### 更正（重要）

`archives/w/websocketpp/0.8.2/` 的说明里第 3 条"上游用例使用 Boost.Test 旧入口 `init_unit_test_suite`，
Boost 1.90 已删除该入口"——**实测错误**：上游 33 个测试源文件全部用现代
`BOOST_TEST_MODULE` + `#include <boost/test/unit_test.hpp>`，`grep -rn init_unit_test_suite test/`
在源码里零命中（唯一命中来自上游误提交进 tarball 的二进制 `test/http/test.out`，`strings` 级别的历史残留）。
真正的断口是"该入口需要已编译的 `libboost_unit_test_framework`，而本版本 pin 的 boost/1.90.0.4 包里
没有它"（见 §遇到的问题 第 5 条，含 `conan cache path` 实测）——这一点由补丁 0004 解决，不需要等上游。

### 2. 采用的方案：测试专用补丁 + 自研 CMake harness + ctest 接入 `build()`

```
build() → apply_conandata_patches（0001-0005）
        → _run_upstream_tests():
             CMakeToolchain + CMakeDeps（generate()）
             cmake.configure(build_script_folder="upstream_tests", variables={boost/openssl 绝对路径})
             cmake.build()
             self.run("ctest --output-on-failure", cwd=self.build_folder)
             _emit_hmbs_upstream_marker()  →  HMBS_UPSTREAM_TEST_RESULT=<json>
```

- harness 只做**测试目标**的构建，不参与打包：`package()` 仍只 copy `websocketpp/**/*.hpp` + `COPYING`，
  产物与 0.8.2 逐字节相同。
- `ctest` 失败会让 `conan create` 失败（等同 `make check`），满足 layer-1 定位；
  日志里出现字面 `ctest`，命中 CI `build_and_test.sh` 的 L1c 上游测试执行门禁。
  （不用 `cmake.test()`：它走 CMake 的 `test` 目标，日志里只有 `cmake --build . --target test`，
  看不到 ctest 命令本身，且按 conan-io/conan#12407 不转发 `--output-on-failure`。）
- 紧跟其后的一行 `HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...,"discovered":31,"passed":31,"failed":0}`
  是上游测试扫描器的机器可读口径（本仓库 240 个配方采用同一约定）。数字由 `_emit_hmbs_upstream_marker()`
  再跑一次 ctest、从其汇总行 `100% tests passed, 0 tests failed out of 31` 正则解析得到，**不硬编码**；
  解析不到时按实际输出如实给 0，不伪造通过。代价是套件多跑一遍（+17s）。
- 31 个 `wspp_test()` 目标，每个 `add_test(... COMMAND <bin> --report_level=short)`；`-O0` 保持套件在 CI 里快。

### 3. 为什么"31 个二进制"是全集，而不是"只跑了一半"

- `SConstruct` L220 的 `to_test` 列出 13 个目录：utility、http、logger、random、processors、
  message_buffer、extension、transport/iostream、transport/asio、roles、endpoint、connection、transport；
  这 13 个目录的 SConscript 里共有 **31 个 `env.Program('..._boost', ...)`**（`grep -c "Program(" | 累加`），
  harness 与之一一对应（含 `test/connection` 的两个 TU 合成一个二进制）。
- 上游的 `_stl` 版本不是额外用例：SConscript 用 `env_cpp11.Object('uri_stl.o', ["uri.cpp"])` 从
  **同一批 .cpp** 再编一遍，唯一区别是 `env_cpp11` 带 `-D_WEBSOCKETPP_CPP11_STL_`（SConstruct L164/L170）。
  而 `common/cpp11.hpp` 的门控是
  `defined(_WEBSOCKETPP_CPP11_STL_) || __cplusplus >= 201103L || defined(_WEBSOCKETPP_CPP11_STRICT_)`，
  clang 15 基线即 `-std=gnu++17`（上游 base env 也没加 `-std=`），所以在本工具链下该 define 是**冗余**的：
  harness 编出的 31 个二进制已经同时具备"Boost.Asio 传输 + std 记忆/函数/随机库"，即 `_boost` 与 `_stl`
  两种 flavor 在本环境的实际配置。真要覆盖差异，需要的是 ASIO_STANDALONE 组合（见 §已知限制）。
- `to_test` 目录内的 35 个 `.cpp` 与 31 个二进制的差额，正是下面 3 个**上游自己不构建**的文件 +
  `connection_tu2.cpp`（并入 `test_connection`）。

### 4. 设备端结果（2026-08-30，$HOME/tmp/wspp-harness-build，profile `ci/conan/profiles/ohos-aarch64`）

```
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 31
Total Test time (real) = 17.36 sec     # rc=0

$ 逐个二进制再跑一次 --report_level=detailed（取模块级汇总）
  31 binaries / 316 test cases / 1590 assertions，全部 rc=0
  （逐条数据：$HOME/tmp/wspp-harness-build/assertions.txt）
```

通过率：**31/31 = 100%**（对应评审要求第 1 条"绕过 scons，用 g++/CMake + Boost.Test 真跑并给出真实通过率"）。
断言数按 Boost.Test 运行时报告统计（不是宏站点静态计数）：例如 `test_http` 574、`test_hybi13` 217、
`test_permessage_deflate` 200；`test_extension_permessage_compress` / `test_iostream_base` /
`test_iostream_endpoint` 三个是**编译期/实例化用例**，各跑 1 个 test case、0 条运行时断言（如实记 0）。

### 5. 逐条声明的未覆盖源文件（评审要求第 4 条"1-e 逐项声明"）

这 3 个文件**不在上游 SCons 的构建清单里**（不是"跑失败的用例"），因此 harness 也不构建它们：

| 文件 | 证据 | 判定 |
|---|---|---|
| `test/message_buffer/pool.cpp` | 不在任何 SConscript 的 `Program`/`Object` 清单；源码引用 0.8.2 已删除的 processor/pool 旧接口，设备端直接编译报成员不存在 | 上游自身已废弃的死代码，非用例 |
| `test/transport/hybi_util.cpp` | 同上不在清单；文件 `#include "../../src/..."`，`src/` 目录自 0.3.x 起不存在于 tarball | 上游遗留文件，非用例 |
| `test/processors/parser_perf.cpp` | 同上不在清单；无 `BOOST_TEST_MODULE`（33 个用例文件才有），是手工性能测量 `main()` 工具 | 性能工具，非单元用例 |

除这 3 个文件外，`to_test` 覆盖到的全部上游测试源码都在跑的 31 个二进制里。

### 6. 若必须走 scons（评审要求第 2 条）

`pip3 install scons` 仍不能解锁：它只解决"scons 不存在"，解决不了 SConstruct 的 Python-2 语法
（`has_key` 在 Python 3 已删除，scons 4.x 只跑 Python 3）和 `stage/lib` 树要求，而修 SConstruct 属于
改上游构建系统且不随包分发。因此选择"补丁测试源码 + 自研 harness"，并把上面的对照证据留在本节。

`test_package/` 仍保留（消费者视角：`find_package(Websocketpp)` + 一次真实 `ws://` 回环会话，38 断言），
与本节的上游 layer-1 测试是两层不同的东西，互不替代。

## 注意事项

1. **本版本与 0.8.2 的取舍**：下游只需要 asio（不链 boost 编译库）时用 `websocketpp/0.8.2`；
   下游需要 boost 已编译组件（thread/program_options/…）时用 `websocketpp/0.8.2.1`。
   两个版本都要留在归档里，不要在 PR 里合并或删除对方。
2. **软件级索引冲突提醒**：`archives/w/websocketpp/manifest.yaml` 与 `README.md` 两边都会追加自己的
   版本行，PR #7052 与本 PR 在合并时**可能在这两个文件上冲突**（编辑者取并集即可，两行版本记录都保留）。
3. `packaging/`、`reports/`、`.ci-result.json`、`test_package/build/` 均被 `.gitignore` 覆盖，
   不入库（`packaging/*.tar.gz` 只是本地留档，制品分发走 conan upload）。
4. 本包不产出可执行文件 → 无 `commands.json`（R38 不适用）。

## 已知限制（逐条如实）

1. 设备端验证 ≠ CI 验证：本版本仍需远端 CI 绿灯与评审通过才算完成。
2. TLS(`wss://`) 真握手未测（会话测试走 `ws://` 明文）。上游 `test_asio_security` 只覆盖 TLS 上下文
   构造与错误路径（2 条断言），不做真握手。
3. `ASIO_STANDALONE` 分支未在本设备编译验证（设备无 standalone asio）；
   boost<1.88 的 `#else` 老路径同样未实测（设备只有 boost 1.90/1.91 缓存）。
4. `strand::wrap()` 的 `-Wdeprecated-declarations` 告警未处理（约 32 条），改 `bind_executor()` 需动
   websocketpp 十余处 handler 包装，超出依赖项 PR 范围。
5. **上游测试只覆盖 boost-asio 一种组合**：harness 构建的是 SCons 的 31 个 `_boost` 目标；
   `_stl`（`-D_WEBSOCKETPP_CPP11_STL_`）在同一批源文件上重复，本工具链下该 define 冗余（见 §上游测试 3），
   所以未再编一份 62 个二进制；standalone-asio flavor 则需要设备根本没有的 standalone asio。
6. 3 个上游自己不构建的源文件未纳入（`pool.cpp`/`hybi_util.cpp`/`parser_perf.cpp`，逐条证据见 §上游测试 5）。
7. `test_extension_permessage_compress`、`test_iostream_base`、`test_iostream_endpoint` 各跑 1 个
   test case 但运行时 0 断言（上游用例本身只做实例化/编译期校验），统计时按 0 计，不计入"有效断言"。
8. 逐用例的断言计数（1590 / 316 cases）来自独立 harness 目录下把 31 个二进制再用
   `--report_level=detailed` 跑一遍得到的运行时报告；配方内 `ctest` 用 `--report_level=short`，
   只保证"31/31 通过与否"这一门禁，不重复输出计数。两者是同一批二进制、同一套编译产物。

## 会话决策记录

### 对话 #1 — 改 0.8.2 的 pin 还是新开 0.8.2.1
改已提交配方的 pin 最省事，但会让 #7052 的审计结论与 CI 证据（针对 boost/1.90.0 组合验证）失效，
且违反"不修改他人/已提交归档以顺手迁就下游"的边界。选 R37 后缀机制新开版本，
两份配方各自对应一个可复现的依赖组合。

### 对话 #2 — 要不要顺手把 1.91.x 也纳进来
1.91.x 有 `random`，看着更"全"，但实测其包 include 树里**没有 `boost/asio`** →
websocketpp 在其上根本无法编译，直接排除。选型依据是**包内容实测**，不是配方声明。

### 对话 #3 — 上游测试放哪：layer-1 进 `build()`，还是 CI 侧外挂脚本
评审给的口径是"适配器职责"，两条路：
- A：在 `build()` 里打测试补丁 + 自研 CMake harness + 直接跑 `ctest`；测试失败即 `conan create` 失败。
- B：配方不动，CI/脚本在包外单独编测试。

选 A。B 会让"上游测试"退化成流水线附件，任何直接 `conan create` 的用户（含下游 autobahn 积分赛）
都拿不到这层保护，而且 TEST_QUALITY_SPEC 的 layer-1 定义就是"在配方 build() 内执行"；
代价是配方多 20 行、导出多一个 `upstream_tests/` 目录，可接受。

### 对话 #4 — harness 放哪、0.8.2 那份错误声明要不要回改
- harness 随配方 `export_sources()`（`upstream_tests/CMakeLists.txt`），不下载第三方测试树：
  测试源码本来就来自上游 tarball 的 `test/`，harness 只是构建描述，这样补丁编号 0001-0005
  与 harness 在同一可复现闭包里。
- 0.8.2 归档里"上游测试不可运行"的第 3 条理由写错了（`init_unit_test_suite`）。**不回改 0.8.2**：
  它已过审计与 CI，改它会作废那份证据链，且属于"改他人已提交归档"。改为在本版本 notes 与
  `test_package/MANIFEST.yml` 里明确更正并给出实测命令，评审时一并看。

## 结束标记

**编译结束**: 2026-08-28 18:0x（设备端 conan-verify 全绿；W3 由 finish 写入 `.ci-result.json`）
**最终状态**: built
---

**编译结束**: 2026-08-29 19:44
**最终状态**: built
---

**编译结束**: 2026-08-30 12:3x（上游测试接入后设备端端到端 conan-verify 全绿：build() 内 ctest 31/31）
**最终状态**: built（`published` 只在合并后的 release 流水线确认上传后使用）
