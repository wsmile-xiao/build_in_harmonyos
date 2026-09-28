# trompeloeil-cpp 49 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 是 header-only INTERFACE library）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK clang/clang++（aarch64-linux-ohos），Conan 2.x（OHOS 适配版）
- 构建主机: B 机（HarmonyOS PC aarch64），CONAN_HOME=~/tmp/ch/home-trompeloeil-cpp
- 上游版本: tag `v49`，Conan 版本号 `49`（逐字相等，未归一化），许可证 BSL-1.0
- 补丁: 无（`patches: {}`，上游源码与测试用例均未修改）

## 源码与哈希（本窗一手核验；W4-02/W4-04 已按落盘输出件重写）

- 官方源: `https://github.com/rollbear/trompeloeil/archive/refs/tags/v49.tar.gz`
- tag 形态实测（B 机 2026-09-27 复测，输出件 `~/tmp/uc2/z74-trompeloeil/lsremote-mirror.txt`
  共 50 行）: 全表里匹配 `refs/tags/49`/`refs/tags/v49` 的只有第 45 行
  `eaeb89c1ce9d354b0ba7eb921fd5712cdbd78adf	refs/tags/v49` ⇒ 上游**没有**裸 tag `49`；
  再按 `curl --connect-timeout 20 -m 30` 直取 `.../tar.gz/refs/tags/49` 实测
  `http=404 size=14`（`probe-s8-output.txt:5`），同法取 `refs/tags/v49` 得
  `http=200 size=336774`（同件 7）⇒ 归档 URL 必须带 `v` 前缀。
- 官方 tarball sha256（本窗实测）:
  `2523571fb7920b2813cbc23b46e60294aba8ead7eba434bfec69c24408615593`
  B 机同一 URL 三次独立取档 sha256 逐字同值、各 336774 B
  （`probe-s8-output.txt:19/22/25`，time 2.06s / 0.90s / 1.81s），
  与仓内既有缓存件 `sha256sum` 同值（`probe-output.txt:72`，336774 B）。
- Debian 池件 `trompeloeil-cpp_49.orig.tar.xz` sha256 实测
  `5213c194d3bb417a79cb498be53d0536da9d6a0397845e6a80fecb2df0ba7e4d` / 291284 B
  （`probe-output.txt:78`，与台账全值逐字相等）。
- 两棵树的 `diff -rq`（W4-04：本轮**真做过**，上一轮的"0 行差异"是空比较，见下）：
  命令与逐字输出见 `probe-output.txt`——`tar xzf <官方件> -C official-v49` 退出码 0
  （:118）后 `diff -rq official-v49/trompeloeil-49 dl/x/trompeloeil-cpp-49`
  （:123）报 `diff_rc=0`（:124）、`tdiff_real_lines=0`（:125），
  输出件 `~/tmp/uc2/z74-trompeloeil/tdiff-real.txt` 实测 0 字节；两树顶层条目均 15 个
  （:120、:122）、文件数均 123（:128、:129）；
  `include/` 子树同样 0 差异、各 24 个 `*.hpp`（:136 之后两行）。
  ⇒ 池件与官方件是同一 upstream 的两种压缩打包、内容等价；池件**只作版本/内容交叉核验，
  不写入 conandata.yml**（PF7 重打包源）。
- 上一轮那句"两棵树 `diff -rq` 结果 0 行差异"**不成立并已删除**：当时的命令是
  `diff -rq gt dl/x/trompeloeil-cpp-49`，而左侧 `gt` 是 `git clone` 的目标目录，
  克隆失败后根本不存在（`gt` 不在本机：`probe-output.txt:12` 的
  `gt -> ABSENT`，`gt_dir_exists=NO` 见 :67）；由此产生的
  `~/tmp/uc2/z74-trompeloeil/diffreport.txt`（:93 记 `old_diffreport_lines=18`）
  **不是树差异**：18 行全是单侧 `Only in x/trompeloeil-cpp-49: <条目>`
  （逐字见 :95-112，统计 `only_in_lines=18 / differing_lines=0`
  见 :114、:115），也就是"活着的那一侧"把 15 个顶层条目加
  `.gitattributes/.github/.gitignore` 三个点开头条目整个列了一遍。逐项复核后
  这 18 个条目在官方树里同样存在（:143-160 全为
  `official-has / pool-has`）⇒ 既不是"上游 `test/` 未随包安装"，也不是 harness 生成件，
  纯粹是缺比较对象造成的假输出。
- B 机侧网络实测（重要披露；2026-09-27 02:51/02:59 复测，逐字输出件
  `~/tmp/uc2/z74-trompeloeil/probe-output.txt`、`probe-s8-output.txt`、
  `lsremote-direct.txt`）：
  * `github.com:443` **仍不可直连**：`curl -I` 20s →
    `curl: (28) Operation timed out after 20001 milliseconds with 0 bytes received`
    （`probe-output.txt:32`）；`curl -L -m 65` → `http=000 size=0 time=65.003883`
    （:36）；`timeout 70 git clone --depth 1 --branch v49` →
    `Failed to connect to github.com port 443 after 65472 ms: Couldn't connect to server`、
    `clone_rc=128`（:65、:66）；直连 `timeout 40 git ls-remote --tags`
    超时且输出件 `lsremote-direct.txt` 实测 0 字节。
  * 但 `codeload.github.com` 本轮**可达且完整**：同一 URL 两次分别
    `http=200 size=336774 time=2.965650`（:25）与 `time=2.710905`（:28），
    `remote_ip=20.205.243.165`；`raw.githubusercontent.com` 取 v49 README 为
    `http=200 size=7908 time=0.341763`（:41），落盘 `downloaded_bytes=7908`
    （:42）＝响应头 `Content-Length: 7908`（:47）全量；
    `api.github.com` 为 `http=200 size=4794 time=0.890729`（:61）。
  ⇒ **上一轮申报的"codeload 20s/65s 两次超时"与"raw 90s 只回 2756/7908 B 截断"两条读数
  本轮不复现，已据实删除**；受影响面收窄为 conandata 声明的 `github.com` 主机名本身
  （以及 git 协议克隆）。本轮 W3 的源码由 harness 在验证期临时注入镜像取到（见
  "平台侧披露"），`conandata.yml` 只保留官方 URL（第 14 行，镜像属 PF7 黑名单）。
  ⇒ **本地绿不代表 CI 绿**：CI 侧必须能直连官方 URL，或走仓内镜像 fallback。

## R51 上游测试清点（一手命令与结论，作用于官方 v49 树）
- `find . -type f | wc -l` = 123；`find include -type f | wc -l` = 24
  （`*.hpp` 全树 27 个，`*.h` 0 个）⇒ 台账“101 个头文件”**不成立**，实测 24 个公共头文件
- `grep -rn 'add_test|enable_testing|include(CTest)|catch_discover_tests' CMakeLists.txt test/CMakeLists.txt`
  = **0 命中** ⇒ 上游没有注册任何 ctest 用例
- `grep -n 'option(TROMPELOEIL_BUILD_TESTS' CMakeLists.txt` = `option(... off)`
  ⇒ 上游测试默认不构建，需显式 `-DTROMPELOEIL_BUILD_TESTS=YES`
- 上游测试实体：3 个可执行目标 `self_test`（compiling_tests.cpp + _11.cpp +
  _14.cpp，C++20 追加 test_co_mock.cpp）、`thread_terror`、`custom_recursive_mutex`；
  测试源码行数 `wc -l test/*.cpp test/*.hpp` = 14736
- 负向编译：`compilation_errors/` 下 expect-to-fail 用例，由 `check_errors.sh` +
  `verify_compilation_error.sh` 驱动（check_errors.sh 依赖 GNU parallel）
- 测试期依赖：`find_package(Catch2 3)` / `Catch2 2...<3`，失败则 `file(DOWNLOAD`
  从 GitHub 抓 catch.hpp（构建期联网，必须预置 Catch2）；另 `find_package(Threads REQUIRED)`

## 本轮 W3 实测
本轮 conan create 的逐套件读数（Catch2 断言数/用例数、负向编译 PASS/FAIL 计数、
test_package 断言数）在 finish 完成后追加到本文件末尾，并同步 reports/test-report.md；
未实测前不写任何数字（rule4：声明 ≤ 实测）。

## 本轮 W3 实测读数（本窗一手，包名 trompeloeil-cpp/49；W4-01 改名后重跑）

W4-03 更正：上一轮把下表来源件写成 `reports/conan-create.log`（实算 152 行）却标到
211/214/215/307 行，行号超出该文件长度。本轮逐条重算并改为按实物引用：主载体是
`reports/w3-local-ci.log`（实算 435 行，sha256 `ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`），
`reports/conan-create.log`（实算 152 行，sha256 `8d764881ddffd0a614d2e47879698c01ef89428936b830666b8afea7fc93a731`）只承载 test_package
消费者那一行，故作为并列出处。下表行号由脚本从两份日志 grep 得到，读数取原文逐字。

| 套件 | 标准 | 原文读数 | 出处（文件:行） |
|---|---|---|---|
| `self_test`（Catch2 v3，上游未改） | C++14 | `All tests passed (1361 assertions in 604 test cases)` | `reports/w3-local-ci.log:243` |
| `self_test`（含 `test_co_mock.cpp` 协程） | C++20 | `All tests passed (1394 assertions in 615 test cases)` | `reports/w3-local-ci.log:308` |
| `thread_terror` | C++14 | `RUN: .../build-cxx14/test/thread_terror`，无 FAILED 行 | `reports/w3-local-ci.log:246` |
| `custom_recursive_mutex` | C++14 | `RUN: .../build-cxx14/test/custom_recursive_mutex`，`Pass! (the program compiled)`（`w3-local-ci.log:251`） | `reports/w3-local-ci.log:250` |
| `compilation_errors/`（68 用例） | C++14 | `trompeloeil-cpp/49: [negative-compile c++14] cases=68 executed=50 pass=50 fail=0 excluded=18` | `reports/w3-local-ci.log:311` |
| `compilation_errors/`（68 用例） | C++20 | `trompeloeil-cpp/49: [negative-compile c++20] cases=68 executed=68 pass=68 fail=0 excluded=0` | `reports/w3-local-ci.log:312` |
| test_package 消费者（Catch2） | C++14 | `All tests passed (5 assertions in 4 test cases)` | `reports/w3-local-ci.log:404`（并列出处 `reports/conan-create.log:150`） |

五维记账（rule4：声明 ≤ 实测）：

- **静态总数**：上游不注册任何 ctest 用例（`add_test`/`enable_testing`/`include(CTest)`/
  `catch_discover_tests` 在 `CMakeLists.txt` 与 `test/CMakeLists.txt` 共 **0 命中**）；
  测试实体 = 3 个可执行目标 + 68 个 expect-to-fail 编译单元，测试源码 14,736 行。
- **静态可执行面（条目数）**：3 个自测可执行目标（`self_test`、`thread_terror`、`custom_recursive_mutex`）
  + 68 个 expect-to-fail 负向编译单元 + 1 个消费者程序 = **72 个条目**（这一行的单位是"条目"）。
- **运行时用例数（断言面）**：`self_test` 两轮 604（C++14）+ 615（C++20）= **1219 个运行时用例**；
  另有独立程序 2 个（`thread_terror`、`custom_recursive_mutex`）、负向编译 `executed` 50/68（18 项由上游
  `// exception:` 规则排除）、消费者 4 用例 5 断言 ⇒ ⛔ 把"条目数"与"运行时用例数"用等号串起来（r1/r2 的
  W4-05 口径混用点即此，与 `reports/test-report.md` 的量纲现已分行对齐）。
- **实测通过**：604/604 与 615/615（断言 1361 与 1394）、独立程序 2/2、
  负向 50/50 与 68/68、消费者 4/4（断言 5）。
- **跳过**：18 个负向用例按上游自带 `// exception:` 规则排除（C++14 轮），非本包裁剪。
- **失败**：0 + 0 = 0。`grep -n "ERROR|error:" reports/conan-create.log` 无输出。

W3 门禁四字段（`.ci-result.json`，该件被 .gitignore 覆盖不入 PR，值抄录于此）。本轮 recipe revision
**先后换过两档**：①W4-01 改 `package_info()` 的 CMake 导出名；②把 `conandata.yml` 从 harness 注入态还原成官方
URL。绿跑日志绑定 `#25e761fbcb34ada2255b27369fc16c44`，最终交付态是 `#227d4eb61c6334d5a48de5f872754bcb`
（两档之间的字节差异取证见下面「平台侧披露」节）⇒ 本窗按交付态把全部读数重取了一遍：
`exit_code=0`、`step=W3_local_ci`、`integrity_hash=186d57017ea6c08c`、
`log_sha256=ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`、`timestamp=2026-09-27T03:20:48.937404`。互证：`sha256sum reports/w3-local-ci.log`
实算 `ce7cc4156299de7f7a36885c98da7e63022bb590eafd0bcb4f505c58d2f16569`，与 `log_sha256` 逐字相等。W3 门禁自身失败步骤：无（`exit_code=0`）；`finish` 整体的 step5b/step8 缺口见下「平台侧披露」节。
本地 CI 判决行：`G0_RESULT=pass`（`w3-local-ci.log:23`）、`KC_RESULT=pass`（`w3-local-ci.log:65`）、`JC_RESULT=pass`（`w3-local-ci.log:92`）、`JC_ERRORS=0`（`w3-local-ci.log:93`）、`L0_RESULT=pass: all checks passed`（`w3-local-ci.log:421`）、`[OK] KC2: 模板占位符残留检测通过`（`w3-local-ci.log:51`）、`L1_RESULT=pass: test_package executed`（`w3-local-ci.log:422`，其真跑凭据在 `:404`）、`L2_RESULT=skip: no bin/ dir`（`w3-local-ci.log:423`——本包 `package_type=header-library`、`bindirs`/`libdirs` 皆空 ⇒ **良性 skip，不是失败也不是通过**）、`L5_RESULT=warn: no artifacts found`（`w3-local-ci.log:425`——同上，无产物属预期形态，⛔ 读成隐藏失败）。

## 双包关系与 CMake 命名（W4-01 整改）

- 本包与**已合入**的 `archives/t/trompeloeil/49` 是同一 upstream（rollbear/trompeloeil
  tag `v49`）的两枚配方：除 `conanfile.py` 的 `name` 一行外全文逐字相同，包内头文件与
  include 路径也完全重叠（良性，header-only 头文件名不带包名）。
- 上一轮本包把 `cmake_file_name` / `cmake_target_name` 写成上游名
  `trompeloeil` / `trompeloeil::trompeloeil`，与已合入包字面相同 ⇒ 同一工程同时
  `requires` 两包时，CMakeDeps 会向同一个 `generators/` 目录写**同名**的
  `trompeloeil-config.cmake` / `trompeloeil-config-version.cmake` /
  `trompeloeilTargets.cmake` / `trompeloeil-Target-release.cmake` /
  `trompeloeil-release-armv8-data.cmake`，后写的覆盖先写的，`find_package(trompeloeil)`
  只解析到一枚，另一枚的 imported target 静默丢失。
- 本轮处方是**让名**：本包改用自洽唯一名 `trompeloeil-cpp` /
  `trompeloeil-cpp::trompeloeil-cpp`（`conanfile.py` 的 `package_info()`），并同步
  `test_package/CMakeLists.txt` 的 `find_package(trompeloeil-cpp CONFIG REQUIRED)` 与链接
  target。刻意**不使用** `cmake_target_aliases`/`namespaced_targets` 把上游名复原回来——
  那只会把冲突从 config 文件名搬进 target 名，仍撞。
- 实物互证：改名前遗留在 `~/tmp/uc2/z74-trompeloeil/stale-49/test_package-build/` 的
  CMakeDeps 生成物是上游名五件套；改名后 `test_package/build/` 下重新生成的是
  `trompeloeil-cpp-config.cmake` 等自名五件套；两份实物清单、`new=5 old=5 intersection=0`
  的判据与改名前后 `add_library(trompeloeil::trompeloeil ...)` / `add_library(
  trompeloeil-cpp::trompeloeil-cpp ...)` 两行原文，落盘在
  `~/tmp/uc2/z74-trompeloeil/w4-01-name-disjointness.txt`（判据行 :15，target 行 :17、:18）。
- **消费者口径**：想要上游原生 target 名 `trompeloeil::trompeloeil` 的工程请
  `requires trompeloeil`；本包（`trompeloeil-cpp`）只服务需要按 Conan 包名区分来源、
  或必须与已合入包并存的场景。头文件安装路径与 include guard 未改，两包对消费者提供的
  头内容一致。

## 平台侧披露（不得当成已验证）

- 取源与 harness 回写（本轮实测两类，均未改框架）：
  * `conan-verify` 的 G2 在 `conan create` 前把官方 URL 临时注入镜像，日志原文
    `ℹ️   🔧 E017 预防: GitHub URL 已临时注入 ghfast.top 镜像`（`w3-verify-r2.log` 第 9 行）；
  * W3 本地 CI 的预下载步骤把 `conandata.yml` 的 `url:` 从"单行官方 URL"改写成两元素列表，
    且**不会**自动还原；还原前盘上实物已备份成 `conandata.yml.harness-mutated.bak`，其第 15 行逐字为
    `- "https://gh-proxy.com/https://github.com/rollbear/trompeloeil/archive/refs/tags/v49.tar.gz"`（跑动中途还出现过 `file:///<worktree>/.build-cache/predl_cache/*_v49.tar.gz`
    两枚本地件，属同一改写机制）。
  本窗按"备份 + `git show fd547a140d188cd7580400cefcf82591129a8374:archives/t/trompeloeil-cpp/49/conandata.yml > 原路径`"
  还原（⛔ checkout/restore 路径形式），还原后 `conandata.yml` 第 14 行是官方 URL，
  全文件无 `ghfast`/`gh-proxy`/`file://` 串。
  ⚠ 口径提醒：`conandata.yml` 参与 recipe 导出，还原会让最终提交态的 recipe revision 与绿跑
  日志里的 revision 差这一档文件：绿跑 `#25e761fbcb34ada2255b27369fc16c44`（见 `reports/w3-local-ci.log` 的 `Exported:` 行），还原后 `conan export` 实得 `#227d4eb61c6334d5a48de5f872754bcb`；两枚 `file://` 件的 sha256 与官方 URL 三次独立
  取档同值（见上节 19/22/25 与 72），故源码内容未变，变的只是取源写法。
  ★取证链（W4 r2 的一条 P2，本窗补成他机可核对的形状）：`conan cache path trompeloeil-cpp/49#25e761fbcb34ada2255b27369fc16c44`
  指向 B 机缓存 `p/trompebaf8eb8ebf19/e/`，其中 `conanfile.py` 与交付态 `cmp` **逐字节相同**；`conandata.yml` 只差一个
  hunk `14,16c14`（绿跑态是两条 `file:///.../.build-cache/predl_cache/{320623c7,7cef7f42}_v49.tar.gz`，交付态是第 14 行
  单条官方 URL），两侧 `sha256` 锚点同值 `2523571fb7920b2813cbc23b46e60294aba8ead7eba434bfec69c24408615593`；两枚预下载件
  `sha256sum` 实测均等于该值，与官方 URL 三次独立取档（`~/tmp/uc2/z74-trompeloeil/probe-s8-output.txt:19/22/25`）同值
  ⇒ **被构建、被判定的源码字节与交付态所声明的源同一，差异只在取源写法**。
  ⚠ 诚实边界（评审按此读，⛔ 当成"同一 rev"）：绿跑态那份 `conandata.yml` 的字节形态只存在于 B 机本地缓存，
  盘上的注入备份是**另一档**（`gh-proxy` 两元素列表，`conan export` 实得 `#5b752da75d75c778d6354f4e204f9645`，
  既不等于绿跑 `#25e761fb…` 也不等于交付 `#227d4eb6…`）⇒ 该 rev 桥在他机上不可复推，本段即为披露凭据。
  B 机对 `github.com` 主机名不可直连、三条子域可达的逐字读数统一记在"源码与哈希"节。
  ⇒ **本地绿不代表 CI 绿**：CI 侧必须能直连官方 URL，或走仓内镜像 fallback。
- finish 的失败步骤（本轮重跑逐字，`finish-r2.log`）：`⚠️  失败步骤: step5b, step8`（第 112 行）、
  知识整理卡上印 `║ STEP_FAILED: Step6`（第 127 行）。step7 报的他人条目知识缺口共 3 条：
  `⚠️      E219.kv: root_cause 为空`（:82）；`⚠️      E253.kv: root_cause 为空`（:83）；`⚠️      E305.kv: root_cause 为空`（:84）；step8 `⚠️   gen_summary 失败: 'str' object has no attribute 'append'`（第 101 行）。均为仓级既有缺口，与本包无关，未动框架。
- header-only ⇒ 无 `bin/`，不需要 `commands.json`；`package_type = "header-library"`。
- C++ 标准：上游 `test/CMakeLists.txt` 默认 `CMAKE_CXX_STANDARD 14`，本配方显式跑
  C++14 与 C++20 两轮；编译器 OHOS clang 15 / libc++（`-stdlib` 未改），
  上游 `-Werror` + `-Weverything` 组合下零告警通过。

---

**编译结束**: 2026-09-27 03:07
**最终状态**: built


## 发现与知识（收口窗按版本级 `manifest.yaml` 的 `knowledge_ref`/`knowledge_gained` 逐条交代）

- ✅ **E002 applied**：设备 `/tmp` 只读 ⇒ 本包全部临时件、探针输出与测试工作目录改走 `~/tmp/uc2/...` 与 `$TMPDIR`；
  一手判据：向 `/tmp/x` 写入返回 `can't create ... Read-only file system`。
- ✅ **E017 consulted（未采用其处方）**：`error_signature` 为 GitHub 连接超时的镜像条目；本包取源最终**直连
  `codeload.github.com` 成功**（`http=200 size=336774 time≈2.7-3.0 s`，逐字见 `~/tmp/uc2/z74-trompeloeil/probe-output.txt`
  与 `probe-s8-output.txt:19/22/25`），受影响面收窄为 `github.com` 主机名（`-I` 20s 超时、`-L` `http=000/65.003883`、
  `git clone` `rc=128`、直连 `ls-remote` `rc=124` 且 0 字节）⇒ **没有**注入镜像 URL 交付，只取该条的"可达性先实测再归因"口径。
- ✅ **DRAFT-11301-ohos-compile-fail-suite applied**：header-only 库的"编译期失败即用例"家族（本包 68 个
  expect-to-fail 编译单元的处置与 excluded 归因按该条口径，一手：上游 `verify_compilation_error.sh:31/34`）。
- ✅ **同族既有归档 `archives/t/trompeloeil/49` consulted ⇒ 判为必须让名**：两包 `conanfile.py` 全文只差 `name`
  一行、`cmake_file_name`/`cmake_target_name` 逐字相同 ⇒ 同工程双 `requires` 会互相覆盖 CMake config；
  本包改名为 `trompeloeil-cpp` / `trompeloeil-cpp::trompeloeil-cpp`，⛔ 用 `aliases` 复原上游名。
  判据一手：新/旧 CMakeDeps 生成件各 5 枚、**文件名集合交集 0**（`~/tmp/uc2/z74-trompeloeil/w4-01-name-disjointness.txt:15-18`）。
- ✅ **Catch2 构建期联网下载（`file(DOWNLOAD .../catch.hpp)`）consulted**：本包 `test_package` 不使用该路径，
  消费者测试只链本包头 + 真跑，故不构成本包依赖；该机制的沉淀归属同族条目，⛔ 记在本包名下。
