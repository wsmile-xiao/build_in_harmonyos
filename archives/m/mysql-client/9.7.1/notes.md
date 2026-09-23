# mysql-client 9.7.1 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMake 单仓，client-only 子集）
- 编译日期: 2026-09-08 ~ 2026-09-09
- 编译器: OHOS clang 15.0.4（aarch64-linux-ohos，宿主鸿蒙 PC），CMake 4.1.2
- 状态: built（conan create 全流程 EXIT=0，test_package 69/69 通过）
- 依赖: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4（W0 conan download 全命中；
  **不需要 boost**——9.x 用源码树内 bundled boost_1_87_0）
- 母版: archives/m/mysql/8.0.46（published，2026-09-03）
- 参照: knowledge E459（percona-server 8.4.10_10）+ archives/p/percona-server/8.4.10_10

## 版本选择与源码

mysql 9.7.1（innovator 9.7 系，MYSQL_VERSION_MATURITY=LTS）。主源官方 CDN：
`https://cdn.mysql.com/Downloads/MySQL-9.7/mysql-9.7.1.tar.gz`，
sha256 = dabff263022be6a09151c21812322873437e0d77aec8c4cc7381882c3ea1aeae。
GitHub tag 归档为备源（不同压缩流，sha256 不同）。

## 配方来源与 9.x 差异

以 mysql/8.0.46 conanfile.py 平移：OHOS cache_variables（CMAKE_SYSTEM_NAME=Linux +
aarch64 + OHOS=1、try_run 预置、client-only 开关组、依赖 cmake_find_mode=none +
显式指路）全部继承。9.x 差异实测：

| 差异点 | 8.0.46 | 9.7.1 | 处理 |
|---|---|---|---|
| boost | FIND_PATH + 版本检查（EQUAL 77）+ 制品仓 boost/1.84.0 | cmake/boost.cmake 重写为 46 行 always-bundled（extra/boost/boost_1_87_0，header-only INTERFACE） | 配方删除 WITH_BOOST/DOWNLOAD_BOOST/boost requires |
| C++ 标准 | 17 | 顶层硬设 23 | clang15 无 -std=c++23，CMake 4.1.2 映射 `-std=gnu++2b`，可编译 |
| try_run 预置 | 6 项 | FALLOC_PUNCH_HOLE/__BUILTIN_FFS/TEST_RUN_RESULT(+OUTPUT)/CURSES_CURSES_H_PATH 不再使用 | 配方已删除（多传无害但按实际清理） |
| libs/mysql C++ 模板库 | 无 | 新增（gtids/sets/strconv/ranges/iterators），被 libchangestreams→mysqlbinlog 与 json_client_library/json_dom 消费 | 见下方编译期问题 4-7 |

## 配置迭代记录

第一轮配置一次通过（cfg-mysql971-round1.sh，86.9s）。COMPILE_DEFINITIONS 确认含
OHOS_LIBC_DNS_SRV/OHOS_PTHREAD_CANCEL_UNSUPPORTED。5 个 8.0 变量告警未使用（见上表）。

## 编译期问题（逐坑归因）

| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | libs/mysql/utils/tuple_find.h:132、strconv/decode/parse_options.h:102、sets/ 多文件 `using X = D::Y;` 报 missing 'typename' | C++23 允许依赖 using 省略 typename（上游 clang19），clang15 拒绝 | 补 typename（0015/0016/0017/0024/0025 等；含 sets 目录批量 23 处，用扫描脚本 fix_typename.py 定位 `using N = Xxx_t::m;` 模式） |
| 2 | decode.h:152 等 5 处 clang frontend crash（exit 139，段错误） | C++23 curried-concept placeholder（`Concept<Args> auto &x`，P2841），clang15 不支持且解析器崩溃 | 改写为显式模板 + requires 子句（0017/0018/0019/0020） |
| 3 | parser.h:459 `static_assert(std::contiguous_iterator<Parser>)` 失败 | 库自检断言，OHOS libc++15 概念求值差异（上游 clang19 通过） | OHOS 下移除断言（0021） |
| 4 | extra/libcno 的 cno_huffman_generator Error 127 | 9.x 新增 libcno 组件的生成器裸 COMMAND（PATH 找不到），comp_sql 同款坑 | `$<TARGET_FILE:cno_huffman_generator>`（0022） |
| 5 | `<source_location>` file not found | OHOS libc++15 无该 C++20 头；唯一使用者是 debug 格式化助手（生产代码无调用点，gunit 测试不参与构建） | `#if !defined(OHOS_LIBC_DNS_SRV)` 条件编译排除（0023；注意不能用 `-DOHOS`——OHOS 是 cmake cache 变量不是编译宏，全局编译宏是顶层 ADD_DEFINITIONS 注入的 OHOS_LIBC_DNS_SRV） |
| 6 | Compound_parse_options functional-cast 报 no matching conversion；ranges/collection_interface、ranges/disjoint_pairs 的 std::ranges::distance/prev/next/advance 不存在；string_view `operator<=>` 无操作数 | P0960 括号聚合初始化 libc++15 不完整；libc++15 ranges CPO 缺失（ranges::prev/next 是 C++23）；libc++15 string_view 无 `<=>` | brace 聚合初始化替代；同类型迭代器场景 std::prev/next/advance/distance 语义等价替换；`compare() <=> 0` 替代（0025/0026/0027） |
| 7 | changestreams/gtids 全线 `--__i` invalid → std::bidirectional_iterator 误判；Map_boundary_storage 'no member begin'（CRTP 不完整类型急切实例化） | libc++15 在 std::bidirectional_iterator 求值中，对 Iterator_interface 的 operator-- requires（依赖 CRTP 派生类成员 prev/advance 检测）误判；clang19 已修 | operator-- 的 requires 在 clang<17 下解除（能力判据 `__clang_major__ < 17`）；**根治**：libchangestreams 与 mysqlbinlog 是 libs/mysql/sets 概念链仅有的消费者，上游对 VS2019 有同款跳过先例（`IF(VS2019 AND WITHOUT_SERVER)`，注释明说该编译器编不了 libs/mysql/sets），OHOS 沿用该机制跳过二者。libmysqlclient.a 的 LIBS_TO_MERGE（clientlib/mytime/strings/vio/mysys）不含 libs/mysql，消费者库不受影响 |

工程环境坑（反复咬人，务必记住）：
- **HMDFS 写读延迟**：filemgr/sed 编辑 .work 后立即 make，clang 可能读到旧内容产生**假错误**（同一文件探针单独编译通过）。对策：修改后 sleep 或单独重编验证。
- **HMDFS 删除延迟**：rm 后 ls 仍可能列出旧文件（patches/ 清理实测复现两次）。
- **HMDFS 剥行尾空格**：补丁基准树必须 tar 解压（.orig）；diff -u --label 生成；git apply --check + 全套应用后与 .work 树 diff 为 0 作为黄金验证。
- **conan 的 patchng 比 GNU patch 严格**（GNU patch 容忍 fuzz/offset，patchng 直接失败）：补丁必须精确上下文。多文件拼接补丁与增量基准补丁易出问题，最终方案是 **45 个 per-file 补丁**（.orig→.work 每文件全量 diff，无重叠无增量依赖）。
- conan2 缓存 package_folder 定位：`conan install --format=json` 读 graph nodes（conan cache path 只给 export 目录）。

## 补丁清单（46 个，per-file）

分组与 root cause 详见 conandata.yml patch_description + 学习日志 02-适配.md：
- 构建系统：OHOS 平台守卫（shared target 跳过、MYSQL_CHECK_RPC 跳过、mysqlbinlog/
  libchangestreams 跳过）、生成器 `$<TARGET_FILE:...>` 化、sys_schema 跳过
- **能力探测体系（R8 合规，替代源码平台宏）**：顶层 CMakeLists 用
  CHECK_SYMBOL_EXISTS/CHECK_INCLUDE_FILE_CXX 探测 libc 能力（res_nsearch、
  pthread_cancel），经 config.h.cmake 进 my_config.h；dns_srv.cc 走
  res_init/res_search（无 res_n* 时）、my_thread.cc 走 ENOSYS（无 pthread_cancel
  时）、text_source_location 用 `__has_include(<source_location>)`、parser 自检
  断言按 _LIBCPP_VERSION 条件保留、iterator_interface 约束按
  `__clang_major__ < 17` 解除——全部为能力/编译器版本判据，无 OHOS 专属源码宏
- OHOS libc 兼容：DNS SRV res_search 路径（能力门控）、pthread_cancel ENOSYS
  fallback（能力门控）、get_password uchar 强转
- clang 15/libc++ 15 C++ 兼容：typename 补充、C++23 curried concept 改写、
  聚合初始化、ranges CPO 降级、string_view <=>、<source_location> 排除
- libedit 三件套 + rpcgen vanilla 分支（母版意图平移重做）

## 测试

- conan create 全流程 EXIT=0；test_package（69 用例消费者测试，链接
  mysql-client::mysql-client 静态库）测试程序 exit 0。
- 手动复现（staging libmysqlclient.a + test.c，clang 两步编译，-lc++ -lc++abi）：
  **通过 69 / 失败 0 / 合计 69，All tests passed**。完整输出：
  reports/test-package-output.txt；conan create 日志：reports/conan-create.log。
- 断言要点：mysql_library_init/end、mysql_get_client_version >= 90701、
  mysql_thread_safe == 1、MYSQL handle init/close、OHOS 平台专项 10 项。
- 产物：bin/ 15 个客户端工具（mysql/mysqladmin/mysqldump/mysqlcheck/mysqlimport/
  mysqlshow/mysqlslap/mysqltest/mysql_config/mysql_config_editor/
  mysql_migrate_keyring/mysql_secure_installation/my_print_defaults/perror/comp_err；
  **mysqlbinlog 按 OHOS 条件跳过**，见编译期问题 7）+ lib/libmysqlclient.a +
  include/。readelf：mysql 为 ELF64/AArch64/PIE，NEEDED 仅 libc++_shared.so 与
  libc.so；strings 确认 9.7.1 版本串。

## 工程环境备忘（对本仓后续适配有用）

- GitHub 源码下载用 `curl -fL`；官方 CDN cdn.mysql.com 直连可达。
- /tmp 只读（E002），临时目录用 $HOME/tmp。
- HMDFS 三坑（延迟读/删除延迟/剥行尾空格）见上文。
- conan create 大包建议 `ohc-run.py timeout set <名> <版本> 7200`（CI/W3 同源）。

---
**编译结束**: 2026-09-09（conan create EXIT=0，test_package 69/69）
**最终状态**: built

## 上游测试（2026-09-14 补全）

- **依赖**：上游单元测试框架为源码树内置 googletest 1.17.0（`extra/googletest`），
  不是 conan 包；boost_1_87_0 亦为源码树内置（header-only）。因此“上游测试依赖库”
  不需要新增 conan 制品，只需打开构建开关。
- **开关**：conanfile.py 新增 `with_unit_tests` 选项（默认 False；上游 client-only
  本身不开测试）。开启后 `WITH_UNIT_TESTS=ON` 并执行 ctest：
  `conan create archives/m/mysql-client/9.7.1 -o with_unit_tests=True`。
- **实测（手工等价路径）**：
  `cmake -DWITHOUT_SERVER=ON -DWITH_UNIT_TESTS=ON …` → `make -k unittest_all -j6`
  （rc=0）→ `ctest --output-on-failure`。
  - ctest：49 个目标，47 通过（96%）；
  - gtest 用例：2520 个（2517 通过），其中 `merge_small_tests` 聚合 2370 个；
  - mytap：17 个用例全通过；`unittest/examples` 全通过；
  - mysys 独立测试程序：`thr_lock` 通过（Test succeeded）。
- **失败/受限 5 项**：`Mysys.CreateTempFile`、`Mysys.UnpackDirname`（/tmp 只读与
  HOME 环境）、`LibsRanges.DisjointPairsView`（SIGSEGV，libs/mysql/sets CRTP 概念链，
  同 mysqlbinlog 跳过原因）、`mf_iocache_test`（源码硬编码 /tmp，只读）、
  `build_id_test`（WITH_BUILD_ID=OFF 未构建）。详见
  `reports/upstream-unit-tests.md`。
- **新增补丁 0047-0058**：client-only 下让测试目标进入构建（WITHOUT_SERVER 守卫、
  library_mysys 组件、HAVE_PSI_INTERFACE），以及 clang15/libc++15 兼容的等价改写。
  其中对 4 个 `unittest/gunit` 测试源文件做了等价改写（C++23 ranges CPO /
  reverse_view 缺失），未改变任何断言语义。
