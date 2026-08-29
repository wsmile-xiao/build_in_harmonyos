# websocketpp 0.8.2 适配笔记

> 本文件是 2026-08-28 重做版本。旧版（2026-06-23，clang 18.1.8，status: published）是**伪发布**，
> 全文见 git 历史；重做动机见 §0。

- 软件：websocketpp 0.8.2（C++ WebSocket client/server，**header-only**）
- 类型：库（无 `commands.json`，R38 不适用）
- 依赖：`boost/1.90.0`、`openssl/3.5.6`
- 补丁：3 个（boost≥1.88 / Asio≥1.31 API 兼容层）
- 任务定位：autobahn-cpp 17.5.1-git7cc5d37【积分赛】的**依赖项** PR
- 环境：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）/ clang 15.0.4 / `aarch64-unknown-linux-ohos`
  / conan 2.29.1 / cmake 4.1.2 / python 3.12.8（均设备端 `--version` 现场核对）

## 0. 伪发布史（W0b 历史核验结论）

| 项 | 旧归档（2026-06-23） | 实测核验 |
|---|---|---|
| 源码 URL | `file:///storage/Users/currentUser/.opendesk-tmp/...` | CI 不可复现（本地路径） |
| 配方 | `archives/w/websocketpp/0.8.2/conanfile.py` 不存在 | 从未提交（git 历史无该配方） |
| 制品仓 | status 写 `published` | `conan search websocketpp* -r ohpcd` 0 结果（R35 用 `conan download --only-recipe` 复核） |
| 交付物 | 声称产出 `websocketpp-0.8.2-ohos-aarch64.tar.gz` | 手动打包口径，违反 R16/R18 |
| 关键结论 | "无源码修改，兼容问题全靠 CMake 参数" | 站不住：那是**没编译消费者代码**的结果，见 §3 |
| 关键结论 | "HarmonyOS clang++ 无法链接 C++ 可执行（-lc++ 找不到）" | 本次不成立：test_package 与本地探针均正常链接运行；旧结论绑定当时的 clang 18.1.8 环境，不作为平台事实沿用 |

因此 `manifest.yaml` 状态由 `published` 改为 `pending_ci`，源码 URL/sha256 改为官方源重验。

## 1. 为什么配方不走上游 CMake

上游 `cmake/CMakeHelpers.cmake` 的 `final_target()`（L82）只做
`install(DIRECTORY ... PATTERN *.hpp*)` + 生成 `websocketpp-config.cmake`——**不编译任何对象**。
同时上游 `CMakeLists.txt` 是 `cmake_minimum_required(VERSION 2.8.8)`，在 CMake 4.1.2 下需要
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 才能 configure（E103）。
所以配方 `package_type = "header-library"`，`package()` 直接 `copy()` 头树 + `COPYING`，
不调用上游 CMake：产物等价，且消掉一整类 CMake 4.x / `TRY_COMPILE` 兼容坑（catch2 有同样先例）。

注意：`test_package` 仍用 CMake + `CMakeDeps`，因为要验证的就是消费者的 `find_package(Websocketpp)`。

## 2. 依赖决策

- `boost/1.90.0`：`transport/asio/*.hpp` 经 `common/asio.hpp` 无条件 `#include <boost/asio.hpp>`
  （非 `ASIO_STANDALONE` 时），`common/memory.hpp`/`functional.hpp` 也回落到 Boost。
- `openssl/3.5.6`：`config/asio.hpp` 与 `config/asio_client.hpp` 拉 `<boost/asio/ssl.hpp>`
  → `<openssl/*.h>`。**这是设备端实测出来的**：只 requires boost 时 test_package 报
  `boost/asio/ssl/detail/openssl_types.hpp:23: fatal error: 'openssl/conf.h' file not found`。
  本仓库 `archives/b/boost/1.90.0/conanfile.py` 不 requires openssl（它只导出头 + 
  `unit_test_framework`），所以必须由 websocketpp 传递，否则每个下游都要自己补。
- R36 复核（`conan download <ref> -r ohpcd --only-recipe`，不用 `conan list`）：
  `boost/1.90.0`、`openssl/3.5.6` 均可下载 ✓。
  注：`boost/1.76.0` 用同法报 `system acceleration policy not enabled` → 按未发布处理，不作 fallback。
- 版本占用（R37）：制品仓无 `websocketpp/0.8.2` 配方，首适配直接用上游版本 `0.8.2`。

## 3. 源码修改清单（3 个补丁，唯一入口 `refresh-patch --auto`）

### 根因

websocketpp 0.8.2（2020）用的是 Boost.Asio 经典执行器 API；**Boost 1.88 起（Asio 1.31）
一次性移除**了这些名字，且上游 master（2026 年 clone 核验）仍在用 `io_service`，无官方修复。
设备端 boost 1.90 缓存实测：无 `boost/asio/io_service.hpp`，有 `executor_work_guard.hpp`，
`BOOST_ASIO_VERSION = 103800`（1.38.0）。

首过 `conan create` 的真实报错（`reports/conan-create.log`）分成 5 类，全部要处理：

| # | 被移除的东西 | 出现位置 | 处理 |
|---|---|---|---|
| 1 | `boost::asio::io_service`（typedef 也没了） | connection.hpp / endpoint.hpp / security/{none,tls}.hpp 的 `io_service_ptr`、`io_service::strand` | `common/asio.hpp` 里 `typedef io_context io_service` |
| 2 | `io_service::work` | endpoint.hpp `work_ptr` typedef、`start_perpetual()` | `typedef executor_work_guard<io_context::executor_type> work`；构造改走 `make_work_guard()`（guard 只有 executor 构造 + 移动构造，旧 `work` 不可拷贝，故这一处保留 `#if`） |
| 3 | `basic_waitable_timer::expires_from_now()`（getter） | connection.hpp ×4、endpoint.hpp ×2，全部是 `is_neg(timer->expires_from_now())` 惯用法 | helper `is_expired(t)` = `t.expiry() <= t::clock_type::now()`（旧路径仍用 `is_neg(expires_from_now())`） |
| 4 | `io_context::post(f)` 成员（只剩 free 函数） | connection.hpp `interrupt()`/`dispatch()` ×4 | helper `post_handler(ios, h)` → `post(ios, h)` |
| 5 | `io_context::reset()`、`socket_base::max_connections`、旧 resolver `resolver::query`/`resolver::iterator` | endpoint.hpp `reset()`、3 处 backlog、`listen(host,service)` 同步解析、`async_resolve()` + `handle_resolve()` 签名 | `reset_io_service()`→`restart()`；`max_connections`→`max_listen_connections`（两代同名同义，无条件替换）；`resolve_endpoints/resolve_empty/resolve_first/log_resolve_results/async_resolve_endpoints` 包装，`handle_resolve` 参数类型换成 `resolve_results` |

### 为什么门控用 `BOOST_ASIO_VERSION` 而不是 `__OHOS__`

这是 **boost 版本兼容**，与平台无关：`__OHOS__` 守卫会把问题错误地绑到鸿蒙上，
非 OHOS 的 boost≥1.88 用户依旧编译失败（R6 要求守卫有实质逻辑，这里逻辑是版本判定）。
门控写成一个宏，两个分支都保留：

```cpp
// standalone Asio: ASIO_VERSION >= 1.31；Boost: BOOST_ASIO_VERSION >= 103100
#define WEBSOCKETPP_ASIO_MODERN 1/0
```

选 1.31/1.88 这一侧的理由：新路径用到的所有 API（`io_context`、`executor_work_guard`、
`results_type`、`expires_after/expiry`、`restart`、free `post`）在远早于该版本的 Asio 就已存在，
所以"门控偏晚"只会让 1.86/1.87 用户保持现状（本来也编不过），"门控偏早"才会引入回归——
不存在偏早风险。**这是版本兼容判断，未在设备上用 boost<1.88 实测（设备只有 1.90/1.91），见 §7。**

helper 命名统一（`resolve_*`、`is_expired`、`post_handler`、`reset_io_service`），
调用点零 `#if`，只有 work guard 构造保留一处版本分支。三个补丁都是 Level ① 源文件改动，
`patch -p1 --dry-run` 干净通过。

### 复现性核验（设备端）

```
$ for p in patches/*.patch; do patch -p1 --dry-run < $p; done      # 3/3 OK
$ cp -r <orig> x && cd x && for p in ...; do patch -p1 < $p; done
$ diff -rq x <work> | grep -v edit-tracker                          # 无输出 → 逐字节一致
```

## 4. 上游测试为什么没跑（三条实证，不猜）

`reports/upstream-test-probe.log` 是原始记录：

1. **SCons 不可用**：`command -v scons` 无输出（设备与 CI 都没有）；且 `SConstruct` 是
   Python 2 专用——L5/8/11/15/25 起大量 `os.environ.has_key(...)`，在 Python 3.12.8 下必崩。
2. **Boost 树形态不符**：`SConstruct` L35 要求 `BOOST_ROOT` 或 `BOOST_INCLUDES+BOOST_LIBS`
   指向 boost 的 `stage/lib` 预编译树；Conan 的 `boost/1.90.0` 包 `lib/` 里只有
   `libboost_unit_test_framework.a`，没有 stage 树。
3. **上游用例的 Boost.Test 入口已过时**：`test/utility/uri.cpp` 编译产物里是
   `T init_unit_test_suite(int, char**)`（旧 Boost.Test 模块入口），而 Boost 1.90 的
   `unit_test_main` 要 `init_unit_test()`；静态库链法报 `undefined symbol: init_unit_test()`，
   header-only 链法（`-include boost/test/included/unit_test.hpp`）报
   `undefined symbol: init_unit_test_suite(int, char**)`。两条路都要改上游测试源码才能通，
   超出依赖项 PR 范围。

结论：**上游 `scons test`（11 目录 / 35 个 .cpp）在本次配置下不可运行**，
按 `TEST_QUALITY_SPEC` 口径以 test_package 复现其测试面，清单与对应关系写在
`test_package/MANIFEST.yml`。这是"环境/上游版本组合导致不可运行"，不是"跳过上游测试"。

## 5. test_package 设计（R28/R34：真调 API + 真跑功能）

因为本包的全部风险都在"模板实例化 + 运行时执行器行为"，只编译等于没测。测试两层，38 个断言点：

1. `unit_checks()`（18）：`uri`（含 `get_resource()` 返回 **path?query** 这一 websocketpp 语义，
   旧测试断言写成 `/ws/v1` 是错的，本次实跑才暴露）、base64 RFC6455 往返、UTF-8 校验、
   close 状态码、user-agent。
2. `session_checks()`（20）：同进程真会话——
   `server<config::asio>` + `client<config::asio_client>`，两个 `io_context` 各由一个线程 run，
   `listen("127.0.0.1","0")` 走**同步 resolver**、`get_local_endpoint().port()` 取 ephemeral 端口、
   `get_connection("ws://localhost:PORT/echo")` 走**异步 resolver**（`/etc/hosts` 实测可解析）、
   `start_perpetual()/stop_perpetual()` 走 **work guard**、`set_timer(10s)` 走 **steady_timer/expiry**、
   `con->interrupt()` 走 **strand + post**、文本帧 echo（`pong:ping`）、
   `close(normal,"done")` 走**关闭握手**，最后断言 `get_state()==closed`、
   `get_remote_close_code()==1000`、`get_remote_close_reason()=="done"`。
3. 双看门狗保证不挂 CI：websocketpp `set_timer` 10 s 停客户端 + `SIGALRM` 60 s `_exit(3)`；
   另加 `set_fail_handler` 捕获失败原因并打印 `get_ec().message()`（首跑就是靠它定位到
   自己漏了 `start_accept()`）。

价值实证：这一层在设备端**首跑就抓出两个问题**——旧测试的 `get_resource()` 错误断言，
以及我自己漏 `start_accept()`；纯编译测试两者都会静默通过。

## 6. 验证记录（设备端实际执行）

```
$ python3 scripts/ohc-run.py refresh-patch websocketpp 0.8.2 --auto
  变更文件 (3): common/asio.hpp, transport/asio/connection.hpp, transport/asio/endpoint.hpp
  生成 0001/0002/0003 三个补丁；manifest.patch_generation 记录
  orig hash 11cb6ad4b227dd71 / work hash 5b3d76e53963ecca（15:18 由 finish 重算）。
  两次 refresh-patch 产出的补丁文件 sha256 **完全相同**
  （29057989… / 022f9de8… / 5bc89dd3…，与 conandata.yml 登记值逐条一致）；
  work hash 变化只覆盖 .work 快照本身（mtime/追踪器文件参与计算），不代表补丁内容有漂移。
$ sh <wrapper> python3 scripts/ohc-run.py conan-verify websocketpp 0.8.2
  G0 G1 G2 G3 G4 L2 L4 L5 全部 ✅ PASS
  `reports/conan-create.log`（16:23，**先 `conan remove websocketpp/0.8.2@ohpcd/stable -c`
  清掉全部本地 recipe/binary 后重跑**，确保不是缓存命中的复跑）：
  L8 导出 3 个 .patch → L102-104 `Apply patch (portability)` ×3 → L189 `Running test()` →
  L191 `test_websocketpp: all checks passed`；`conan-verify-report.md` 中
  G0/G1/G2/G3/G4/L2/L4/L5 全 PASS。
  说明：15:18 finish 内的那次 G2 复跑命中了二进制缓存，日志里没有 Apply patch 行，
  因此不能拿它当"补丁确实被应用"的证据——已在 16:23 用干净重建重取该证据。
$ 稳定性：功能测试连续 5 次 rc=0，单次 ~27 ms
```

补丁首次生效前的一轮 G2 失败（`openssl/conf.h` 未找到）与修复见 §2；再早一轮
（patches 段被 `.ghfast-bak` 回退、实际编译未打补丁源码）的 20 条原始报错，**只保留在 §3
的错误面表格里**——`reports/` 被 .gitignore 排除且该日志已被后续运行覆盖，不构成可交付证据，
故不引用为凭据。可交付的干净证据是 §6 的 16:23 干净重建日志与 W3 日志。

设备端还预跑了 PR diff 级的 CI 垃圾检查（避免白烧一轮 CI）：
`JUNK_PR_DIFF=<(git diff 9b4b44bb4..HEAD) bash ci/scripts/junk_check.sh` →
prdiff 模式 JC1–JC6 全 0 命中，JC6 输出"涉及软件数: 1（合规）"（文件数随收尾提交为 14：
11 个交付件 + 软件级 README.md/manifest.yaml + 1 条知识草稿）。

### 两个工具坑（框架行为，未在框架内改动，按 AGENTS.md 上报）

1. `scripts/ohc/conan_verify.py` G2 的"崩溃恢复"分支会**用残留的
   `conandata.yml.ghfast-bak` 覆盖 `conandata.yml`**，且每次跑完都重新留下该 `.bak`。
   本机上一次会话遗留的 `.bak` 内容正是旧版 `patches: {}`，结果刚登记的 patches 段被静默
   回退，那一轮编的是**未打补丁**的源码（现象：G2 报的还是老错）。
   **对策**：跑 conan-verify/finish 前先 `rm -f conandata.yml.ghfast-bak`，跑完再删一次并
   `cmp` 校验 conandata 未被回退（本次用 `$HOME/tmp/wsscheck/verify.sh` 包装，
   canonical 副本留在 `$HOME/tmp/wsscheck/conandata.canonical.yml`）。提交前该 `.bak` 必须不存在（JC1）。
2. `refresh-patch --auto` 只写 `patches/` 与 `manifest.yaml`，**不更新 `conandata.yml` 的
   `patches:` 段**；不手工补 `patch_file/patch_description/patch_type/sha256` 的话
   `apply_conandata_patches()` 应用 0 个补丁，且失败信息完全看不出原因。

## 7. 已知限制与未覆盖范围

1. **CI 未验证**：以上全部是鸿蒙设备端结果；设备成功 ≠ CI 成功，最终需 W3 + W4 P0/P1 清零 + CI 绿灯。
2. **TLS(wss) 真握手未测**：测试走 `ws://` 明文。`config/asio.hpp`（含 TLS 模板）在补丁过程中
   被实例化编译（探针覆盖 `security/tls.hpp`），但没有跑过一次真实的 TLS 握手/证书校验。
3. **`ASIO_STANDALONE` 分支未编译验证**：兼容层做成两分支共用（`ASIO_VERSION>=1.31` 判定），
   但设备上没有 standalone asio，该路径只做了源码级审查。
4. **boost<1.88 分支未实测**：`#else` 老 API 路径按上游原语义保留，设备只有 boost 1.90/1.91 缓存，
   无法回归验证；若下游要用旧 boost，需另测。
5. **`strand::wrap()` 弃用告警未处理**：Boost 1.90 对 `wrap()` 报 `-Wdeprecated-declarations`
   （本地构建 ~32 条），改用 `bind_executor()` 要动 websocketpp 十余处 handler 包装，
   超出依赖项 PR 的最小改动范围，且当前只是告警不影响结果。
6. **上游 35 个测试 .cpp 未运行**：原因与实证见 §4；对应测试面由 test_package 复现，
   映射关系在 `test_package/MANIFEST.yml`。
7. 本包不产出可执行文件，无 `commands.json`（R38 不适用）。
8. `is_expired()` 与被删除的 `is_neg(timer->expires_from_now())` 只在
   `expiry() == now()` 这一个测量零概率点上判定不同（旧式是严格 `< 0`）。
   设备端核对 boost 1.90 `basic_waitable_timer::cancel()`（`asio/basic_waitable_timer.hpp:407`）
   **不修改 expiry**，只取消挂起的异步操作，因此"定时器被取消"这一路径本来就由调用点的
   前一条件 `ec == lib::asio::error::operation_aborted` 捕获，与本 helper 无关；
   两条腿合起来与旧行为等价。
9. `socket_base::max_connections` → `max_listen_connections` 是**无条件**替换（不留版本分支）：
   后者在本仓库依赖区间（boost/1.90.0，以及 websocketpp 声明支持的 1.49+ 现代 asio）都存在且同义
（`socket_base.hpp:532`）。
   代价是若真有比这更老的 asio（`max_listen_connections` 之前）使用者，需要另加守卫；
   本仓库依赖区间内不存在该情况。

## 8. 下游（autobahn-cpp）已知接口约定

- `cmake_file_name = "Websocketpp"`、`cmake_target_name = "websocketpp::websocketpp"`：
  对齐 autobahn-cpp `cmake/Modules/FindWebsocketpp.cmake` 与上游 `websocketpp-config.cmake.in`。
- `includedirs=["include"]`，`bindirs/libdirs/libs` 置空（header-only）。
- 依赖 autobahn-cpp 的 WAMP 会话会直接踩到 §3 的 5 类 API——即本补丁的复用面。
---

**编译结束**: 2026-08-28 15:18
**最终状态**: built

## 9. 会话决策记录

### 对话 #1 — 伪发布如何处置（2026-08-28，本会话）
旧归档只有 manifest/notes 没有 `conanfile.py`，制品仓 `conan search websocketpp* -r ohpcd` 0 结果，
`notes.md` 里源码 URL 是 `file://` 本地路径。判定为伪发布（§0）。处置：状态改回 `pending_ci`、
URL/sha256 换官方源重验、配方按 header-only 重写，而不是在旧 notes 上打补丁。

### 对话 #2 — 兼容层用版本门控还是平台门控
第一反应是 `#ifdef __OHOS__`（仓库有先例）。否决理由：被移除的是 Asio 经典执行器 API，
与鸿蒙无关，macOS/Linux 用 boost≥1.88 一样编不过；平台门控会让补丁永远无法上游。
最终选 `WEBSOCKETPP_ASIO_MODERN`（`BOOST_ASIO_VERSION>=103100` / `ASIO_VERSION>=1.31`），
`#else` 保留原路径。**这是可上游的形态**，与 R6"守卫必须有实质逻辑"一致。

### 对话 #3 — 只做别名够不够（一次假进展）
第一轮只加 `typedef io_context io_service` 后 G2 仍失败，且错误"少了一半"。复盘确认：
`work`/`expires_from_now`/成员 `post`/`reset`/旧 resolver 都不在别名覆盖范围内。
于是改用 `clang++ -fsyntax-only` + 实例化探针（3 s/轮）先把 5 类错误面全部枚举，
再一次性设计 helper 集合——避免陷入 R43 式调参循环。探针必须真调用成员函数，
否则模板成员不实例化、错误会漏到运行期。

### 对话 #4 — 要不要为跑通上游测试改测试源码
上游 35 个测试 .cpp 用 Boost.Test 旧入口 `init_unit_test_suite`，boost 1.90 不提供。
改上游测试源码 = 第三个补丁集，只服务于测试构建、且属"为跑测试而改测试"，
不在依赖项 PR 最小改动范围内。否决，改为把证据写进 `reports/upstream-test-probe.log`
与 `test_package/MANIFEST.yml`，并说明映射关系。

### 对话 #5 — 交付目录里的 v2 遗留项怎么处理
`finish` step 10 与 `submit` 自检要求 `packaging/*.tar.gz` 与 `reports/test-report.md`。
tarball 与 `.orig/.ci-result.json` 一样被 `.gitignore` 排除（`archives/**/*.tar.gz`、`*.orig`），
所以 `packaging/` 只是本地留档产物（由 conan create 产物目录打包，可复现，不入库、
不违反 R16 的"禁止手动打包制品提交到源码仓"）；CI 侧 JC2/JC3/PF2 也不会看到它。
`packaging/README.md` 写清它是本地产物及其来源。
   另：`finish` step 10 还会提示 `.staging-verified`（v2 autotools 时代 DESTDIR staging 标记）。
   本配方不跑 `make install DESTDIR`，等价验证是 G4 产物完整性（93 个头 + COPYING）与
   包目录清单，因此**不伪造该标记文件**；它不在 `submit` 的阻塞自检项里，只是提示。

## 结束标记

**编译结束**: 2026-08-28 15:19（设备端 W3 本地 CI 模拟通过时刻）
**最终状态**: built
