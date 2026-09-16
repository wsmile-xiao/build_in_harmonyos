# mysql-client 8.4.11 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMake 单仓，client-only 子集）
- 编译日期: 2026-09-10
- 编译器: OHOS clang 15.0.4（aarch64-linux-ohos，宿主鸿蒙 PC），CMake 4.1.2
- 状态: built（conan create 全流程 EXIT=0，test_package 69/69 通过）
- 依赖: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4（W0 conan download 全命中；
  **不需要 boost**——8.4.11 用源码树内 bundled boost_1_84_0，cmake/boost.cmake
  为 always-bundled 形态，无 WITH_BOOST 逻辑）
- 母本: archives/m/mysql-client/9.7.1（feat/mysql-client-9.7.1 分支，PR #9060 在途）
- 参照: origin/feat/mysql-8.4-8.4.11（别队 mysql-8.4 服务端形态，质量以母本为准）、
  archives/m/mysql/8.0.46（已合入 #8023）

## 版本选择与源码

- 8.4.11（maintenance 8.4 系，MYSQL_VERSION_MATURITY 对应 LTS 维护分支）。
- 源: `https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.11.tar.gz`。
- sha256 双源核对：本机 tar 计算值 `eb3051164d625dd346a8203f76e0d5d5d9aec51dbe9d51788e39ec6b3f1394c2`
  == FreeBSD ports `databases/mysql84-server/distinfo`（SHA256 一致，SIZE 479170675 一致）
  == 别队 conandata.yml（同值）。三源一致 ✓。
- 解压：`tar -xzf` 生成 .orig（基准）/ .work（打补丁+构建），两树 diff 为空（干净）。

## 补丁分拣（母本 46 → 8.4.11 18 个）

母本 9.7.1 的 46 个 per-file 补丁对 8.4.11 干净树逐个 `patch -p1 --dry-run`，三类处置：

### A. 直用/微调（10 个，dry-run 干净）

| 补丁 | 文件 | 说明 |
|---|---|---|
| 0004 | extra/libcno/CMakeLists.txt | cno_huffman_generator `$<TARGET_FILE>` 化 |
| 0005-0007 | extra/libedit 三件套 | OHOS 4-byte wchar_t / termcap / 构建 |
| 0012 | mysys/my_thread.cc | pthread_cancel 无 → ENOSYS（能力门控） |
| 0013 | plugin/.../rpcgen.cmake | OHOS 无 rpcgen，用预生成文件 |
| 0014-0015 | scripts(±sys_schema)/CMakeLists.txt | comp_sql `$<TARGET_FILE>` + libmysql 属性 fallback |
| 0016 | sql-common/get_password.cc | uchar 强转 |
| 0017 | strings/CMakeLists.txt | uca9dump `$<TARGET_FILE>` 化 |

### B. 有对应物但漂移，按意图重做（8 个）

| 补丁 | 文件 | 重做要点 |
|---|---|---|
| 0001 | CMakeLists.txt | 能力探测块（res_search/pthread_cancel/res_nsearch/source_location）迁到 8.4.11 位置；MYSQL_CHECK_RPC 与 libchangestreams 加 IF(NOT OHOS)；8.4.11 无 9.x 的 `SET(CMAKE_CXX_STANDARD 23)` |
| 0002 | client/CMakeLists.txt | shared json_binlog/json_binlog_main IF(NOT OHOS)；8.4.11 无 VS2019 门控，mysqlbinlog 无条件构建（可编，见差异表） |
| 0003 | config.h.cmake | 声明 HAVE_RES_NSEARCH/HAVE_PTHREAD_CANCEL（8.4.11 无 source_location 使用点，不需要 HAVE_STD_SOURCE_LOCATION；但与母本一致的探测无害已保留） |
| 0008 | libmysql/CMakeLists.txt | DNS SRV：无 res_n* → libc res_search 置 HAVE_UNIX_DNS_SRV（能力门控）；shared libmysql 与 api_test IF(NOT OHOS)；TARGET 保护 |
| 0009 | libmysql/dns_srv.cc | LINUX_ALPINE → HAVE_RES_NSEARCH 能力门控（替代平台宏，R8 合规） |
| 0010-0011 | libs/mysql/binlog/event/compression/*.h | missing typename ×3 |
| 0018 | utilities/CMakeLists.txt | comp_err/comp_client_err `$<TARGET_FILE>`；comp_err IF(NOT CMAKE_CROSSCOMPILING OR OHOS) |

### C. 无对应物直接就弃（28 个）

- 0012-0038（27 个 libs/mysql 概念链：iterators/ranges/sets/strconv/utils）：
  8.4 的 libs/mysql 只有 binlog/gtid/serialization/utils，无 9.x innovator 的
  sets/strconv/ranges/iterators 模板概念链，对应头文件不存在。
- 0044 sql-common/json_dom.cc：9.7.1 需修 string_view `<=>`，8.4.11 无该用法（C++17
  风格 `compare()` 原生），无对应物。

### 8.4 与 9.x 差异实测（推翻预判的项）

| 项 | 9.7.1（母本） | 8.4.11（实测） | 处理 |
|---|---|---|---|
| boost | bundled boost_1_87_0 | **bundled boost_1_84_0**（cmake/boost.cmake 同样 always-bundled） | 无需 conan boost，配方注释与分层一致 |
| C++ 标准 | 顶层硬设 23 | cmake/libutils.cmake `cxx_std_20` 强制 | 配方 CMAKE_CXX_STANDARD=20 |
| WITH_DNS_SRV | 探测式（LINUX_ALPINE 扩展） | **无显式 WITH_DNS_SRV 开关**（服务端形态别队才有），libmysql 用 HAVE_UNIX_DNS_SRV + LINUX_ALPINE | 沿用母本 HAVE_RES_NSEARCH 能力探测，不采用别队 stub 手法 |
| try_run 预置 | 3 项 | configure.cmake 用 CHECK_C_SOURCE_RUNS：SETNS/CLOCK×2（+innodb FALLOC/FFS、libevent TEST_RUN_RESULT） | 全 6 项预置（8.0.46 同款） |
| `<bit>` | 无 | mysys×3 + serialization 用 std::bit_* | **实测 C++20 下 libc++15 有 `<bit>`** → 别队 4 个 bit 替换补丁基于错误假设，弃用 |
| mysqlbinlog | OHOS 跳过（概念链消费者） | 无条件构建，链接 mysql_binlog_event+json_binlog_static（无概念链依赖） | 保留编译，client-only 可编 |

## 配置迭代记录

第一轮 configure 通过（conan create 内 CMake 配置，2 分钟量级）。COMPILE_DEFINITIONS
确认含 HAVE_LIBC_RES_SEARCH/NO_LIBC_PTHREAD_CANCEL（能力探测生效，无平台宏）。

## 编译期问题（逐坑归因）

| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | **0012-my_thread / 0015-sys_schema 补丁在 conan create source() 阶段失败**（patchng 拒绝："hunk no.1 doesn't match source file"） | conan 的 patchng 比 GNU patch 严格（不接受 fuzz/offset，母本 notes 早有警告）：从 9.7.1 直用的补丁上下文在 8.4.11 有细微漂移，GNU patch 能容差通过但 patchng 拒绝 | 全部 18 个补丁改用 `diff -u --label a/<file> --label b/<file> .orig/<file> .work/<file>` 精确重建，三连验证（git apply --check / 干净树应用 diff=0 / conandata 同步）重跑通过后再 create |
| 2 | `lf_hash.cc:852: no member named 'bit_floor' in namespace 'std'`（strings 之后第一批 C++ 目标编译失败） | **C++ 标准未到位**：conan profile `compiler.cppstd=17` 经 CMakeToolchain 生成的 toolchain 文件（`C++ Standard 17`）**覆盖**了配方 cache_variables 里的 `CMAKE_CXX_STANDARD=20`；8.4.11 顶层 CMakeLists 自身不设标准（靠 `cxx_std_20` feature 逐目标抬升，但部分目标如 mysys_objlib 未被 feature 覆盖）。别队把此误判为"OHOS 无 <bit>"并做了 4 个替换补丁（错误假设） | 与母本同手法：在 8.4.11 顶层 CMakeLists `PROJECT()` 后硬设 `SET(CMAKE_CXX_STANDARD 20)` + `REQUIRED`（进 0001 补丁），覆盖 profile 默认值。修复后 mysys 全过，`<bit>` 四文件直接可用，无需 bit 替换 |
| 3 | 主包 `cmake.build()` 全量构建时误编了 `storage/innobase` 等 server 目标 | （观察日志发现但有条件的路径问题，实际 client-only 下 innobase 只在 configure 期被 try_run 探针引用，未进构建图；此条为预防性记录） | — |

说明：8.4.11 的 `WITHOUT_SERVER=ON` 时顶层仍无条件 `ADD_SUBDIRECTORY(client/utilities/share/libservices)`，`sql/` 跳过；`mysqlbinlog` 不受影响（链接 mysql_binlog_event+json_binlog_static，无 libs/mysql 概念链）。

## 测试

- **上游 libmysql_api_test 在 OHOS 真实执行**（2026-09-15 审查整改）：patch 0008 原先用
  `IF(NOT OHOS)` 整体跳过上游 api_test；现改为按 `IF(TARGET libmysql)` 选择链接目标——
  OHOS 上共享 `libmysql` target 不存在，改为链接静态 `mysqlclient` target，
  `run_libmysql_api_test` ALL 目标保留，因此 `conan create` 的 cmake build 阶段即编译并
  执行上游测试（失败即构建失败）。
  实测输出（构建日志可见）：`There are 133 API functions` /
  `MySQL client library initialized: 8.4.11` / `Done!`，退出码 0。
- conan create 全流程 EXIT=0（Package built + test_package 构建测试执行）；test_package（69
  用例消费者测试，链接 mysql-client::mysql-client 静态库）测试程序 exit 0。
- 手动复现（staging libmysqlclient.a + manual_test.c，clang 两步编译，补 -lc++ -lc++abi）：
  **通过 69 / 失败 0 / 合计 69，All tests passed**（复刻母本 69 用例集，断言基线 >= 80411）。
  完整输出：reports/test-package-output.txt；conan create 日志：reports/conan-create.log
  （107KB < 20MB 未截断，留仓外）。
- 断言要点：mysql_library_init/end、mysql_get_client_version >= 80411、
  mysql_thread_safe == 1、MYSQL handle init/close、OHOS 平台专项 10 项。
- 产物：bin/ 16 个客户端工具（mysql/mysqladmin/mysqldump/mysqlcheck/mysqlimport/
  mysqlshow/mysqlslap/mysqltest/mysql_config/mysql_config_editor/mysqlbinlog/
  mysql_migrate_keyring/mysql_secure_installation/my_print_defaults/perror/comp_err；
  **mysqlbinlog 在 8.4.11 可编译**，与 9.7.1 跳过不同）+ lib/libmysqlclient.a + include/。
  readelf：mysql 与 mysqlbinlog 均为 ELF64/AArch64/PIE；strings 确认 8.4.11 版本串。

## 工程环境备忘（对本仓后续适配有用）

- GitHub 源码下载用 `curl -fL`；官方 CDN cdn.mysql.com 直连可达。
- /tmp 只读（E002），临时目录用 $HOME/tmp。
- HMDFS 三坑（延迟读/删除延迟/剥行尾空格）见母本 notes。
- conan create 大包建议 `ohc-run.py timeout set <名> <版本> 7200`（CI/W3 同源）。

---
**编译结束**: 2026-09-10（conan create EXIT=0，test_package 69/69）
**最终状态**: built

## 提交与 PR

- commit: 3c7b8e81d9 feat(mysql-client): add 8.4.11 HarmonyOS PC adaptation
- 分支: feat/mysql-client-8.4.11（fork，push 成功，Git Hooks PASSED）
  - ⚠️ 分支已按 CI L0n 门禁从任务下发名 `feat/mysql-client-8.4-8.4.11` 重命名（`git branch -m`，非 force push）：
    任务下发分支去前缀后 `mysql-client-8.4-8.4.11` 不含 `mysql-client-8.4.11` → PR #9439 首轮 CI L0n
    branch_name_r40 硬失败（8.0.46 同款先例，见 8.0 归档笔记：旧分支 PR 关闭、合规分支重建）。
  - 重建 PR: #9448 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/9448
    （旧 PR #9439 已关闭；撞车检查无别队 mysql 8.4.11 PR）
- CI/Review 闭环状态：见下（阶段 7 续写）

## 双绿闭环（阶段 7，2026-09-10）

- **CI**：PR #9448 pipeline #43886「CI 校验通过」（Worker CI-017）：Conan test_package 通过 / L0 门禁通过 / L1 门禁通过。
- **AI review**：atomgit-bot「代码审查 ✅ 未发现问题」（note 189148674）。
- 双绿判据达成：最新 commit CI 绿 + AI review 无问题 + 无待回复意见。
- **已停止**：不提审、不再动 PR，等用户手动提审。

## 变更履历

| commit | 说明 |
|---|---|
| 3c7b8e81d9 | feat(mysql-client): add 8.4.11 HarmonyOS PC adaptation（30 文件） |
| 85cdad4531 | docs: record PR creation |
| e6774b5ef4 | docs: record L0n branch rename + PR rebuild 9439→9448 |
| （09-10） | docs: record double-green closure |
| a2dbfaa050 | merge main, union software-level files for multi-version（8.0.46/8.4.11/9.7.1） |
| cf0697e972 | fix(mysql-client): libedit termcap 改用能力探测（AI review Medium 建议） |
| （本次） | fix(mysql-client): OHOS 上真实执行上游 libmysql_api_test（审查 rule4/rule5 整改） |

## 审查整改（2026-09-15，rule4/rule5「上游测试未执行 0/1」）

**审查意见**：`bengbeng2345` / `2402_87729496` 判定 rule4/rule5 FAIL——「上游有用例 1 个
但一个也没测（0/1），无论任何理由均不通过，请解决后真实执行上游测试用例」。

**根因**：patch 0008 为绕过「OHOS 跳过共享 `libmysql` target」导致 `libmysql_api_test`
无法链接，用 `IF(NOT OHOS)` 把**整个上游测试定义与运行目标**一并包掉——上游测试从构建图中
消失，等价于「未执行」。

**整改**：把「跳过测试」改为「换链接目标」——
- `IF(TARGET libmysql)`：非 OHOS 仍链接共享 `libmysql`（行为与上游完全一致）；
- `ELSE()`（OHOS）：链接静态 `mysqlclient` target，上游测试的编译期 `<mysql.h>` 声明检查与
  链接/运行期符号检查全部保留；
- 删除 `IF(NOT OHOS)`/`ENDIF()` 包裹，保留 `run_libmysql_api_test` ALL 目标，
  使测试在 `conan create` 构建期真实编译并执行（失败即构建失败）；
- 补一条 `${CMAKE_COMMAND} -E cat`，把测试 stdout 打到构建日志，便于审阅者直接看到证据。

**验证**：18 个补丁对 pristine mysql-8.4.11 树逐个 `patch -p1` 全部干净应用；
`conan create` 构建日志出现 `There are 133 API functions` /
`MySQL client library initialized: 8.4.11` / `Done!`，上游测试 1/1 通过。

**关于「上游 8983 个 .test」**：`mysql-test/`（MTR 套件，8983 个 `.test`）是 **mysqld 服务端**
的集成测试框架，运行需要启动 mysqld 服务端二进制 + `mysql-test-run.pl`；本包是
`WITHOUT_SERVER=ON` 的 **client-only 库适配**，不构建任何服务端组件，该套件不在适配范围内。
client-only 构建图中唯一的上游测试 target 就是 `libmysql_api_test`（现已在 OHOS 真实执行）。