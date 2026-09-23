# mysql-client-8.4 8.4.11 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMake 单仓，client-only 子集）
- 编译日期: 2026-09-12
- 编译器: OHOS clang（aarch64-linux-ohos，宿主鸿蒙 PC）
- 状态: published
- 依赖（Conan 制品仓全部命中已发布配方）: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4
- 参照: knowledge E459 + archives/m/mysql/8.0.46（同源 8.0 侧完整适配）+ archives/p/percona-server/8.4.10_10（E459 来源）

## 版本选择与打包定位

mysql-8.4 系列 LTS 最新 GA：8.4.11（2026-06-30 发布）。本包是 ConanCenter libmysqlclient 风格的**纯客户端库包**（包名 mysql-client-8.4，仅 libmysqlclient.a + 客户端工具），与仓库既有的 mysql/8.0.46（服务器同源完整包）为同源不同包名并存，互不冲突。

源码走官方 CDN（cdn.mysql.com，GitHub 本机不可达）：sha256 = eb3051164d625dd346a8203f76e0d5d5d9aec51dbe9d51788e39ec6b3f1394c2，tar 50254 文件（zcat 完整性验证通过）。

## 与 mysql 8.0.46 的差异（适配简化点）

| 项 | 8.0.46 | 8.4.11 |
|---|---|---|
| Boost | 需外部 conan boost/1.84.0 + 放宽 boost.cmake minor 检查 | **源码树自带 extra/boost/boost_1_84_0**（INTERFACE 引用），无需外部依赖与补丁 |
| bundled libevent | 存在，try_run 版本探测需预置 TEST_RUN_RESULT | **已移除**（8.4 client 无 libevent），无需预置 |
| try_run 探测 | setns/clock_gettime/clock_realtime/falloc/builtin_ffs/libevent | 仅 setns/clock_gettime/clock_realtime + rapidjson std::regex（CHECK_CXX_SOURCE_RUNS） |
| client json_binlog | shared 目标 + json_binlog_main 测试 | 同构，另有 json_binlog_main_static（静态链接，保留构建） |
| CMake 最低版本 | 3.11.2 | 3.5.1（顶层，未触发 cmake_policy 4.x 问题） |
| bundled libcno（HTTP2） | 无 | **新增**，hpack-data.h 生成器需 TARGET_FILE 化（patch 0015） |

## 补丁策略（15 个：14 个从 mysql 8.0.46 移植 + 1 个 8.4 新增）

直接复用（源码同构，上下文对齐后 git apply 全部通过）：

1. **0001 顶层 CMakeLists**：OHOS 时 ADD_DEFINITIONS(-DOHOS_LIBC_DNS_SRV -DOHOS_PTHREAD_CANCEL_UNSUPPORTED)；`IF(LINUX)` → `IF(LINUX AND NOT OHOS)` 跳过 MYSQL_CHECK_RPC（OHOS libc 无 res_n*）
2. **0002 client/CMakeLists**：`IF(NOT OHOS)` 守卫 shared json_binlog 与 json_binlog_main（其 warning TARGET_COMPILE_OPTIONS 加 TARGET 守卫）；json_binlog_main_static 保留
3. **0003-0005 libedit 三连**：OHOS_LIBEDIT_TERMCAP 定义 + 4 字节 wchar_t 支持 + termcap 手动原型
4. **0006 libmysql/CMakeLists**：DNS SRV OHOS 分支（HAVE_UNIX_DNS_SRV=1 不链 libresolv）；MERGE_LIBRARIES_SHARED(libmysql) 整段 IF(NOT OHOS) 守卫；LINK_FLAG_Z_DEFS/version-script/CLEAN_DIRECT_OUTPUT 加 TARGET libmysql 守卫；libmysql_api_test 与 run_libmysql_api_test 守卫
5. **0007 dns_srv.cc**：3 处 LINUX_ALPINE → `\|\| defined(OHOS_LIBC_DNS_SRV)`（OHOS libc 自带 res_init/res_search）
6. **0008 my_thread.cc**：my_thread_cancel OHOS 返回 -1/ENOSYS
7. **0009 rpcgen.cmake**：`IF(NOT LINUX)` → `IF(NOT LINUX OR OHOS)` 走 vanilla 预生成文件
8. **0010 scripts/CMakeLists**：comp_sql 命令 $<TARGET_FILE:> 化（8.4 原生已有 DEPENDS comp_sql）；GET_TARGET_PROPERTY(libmysql ...) 加 TARGET 守卫回退 mysqlclient 命名
9. **0011 sys_schema**：comp_sql TARGET_FILE 化
10. **0012 get_password.cc**：(uchar *) 强转
11. **0013 strings/CMakeLists**：uca9dump TARGET_FILE 化
12. **0014 utilities/CMakeLists**：comp_err 构建条件 `OR OHOS`（鸿蒙 PC 宿主可直接跑生成器）；comp_client_err/comp_err 命令 TARGET_FILE 化 + DEPENDS 目标

不再需要：0003-cmake-boost.cmake.patch（8.4 无外部 Boost 检查）。

## 配置迭代记录（3 轮）

| 轮次 | 卡点 | 根因 | 解决 |
|---|---|---|---|
| 1 | `extra/libcno` 的 `cno_huffman_generator` Error 127 | 8.4 新增 bundled libcno（HTTP2），生成器命令用裸命令名（E459 模式同款） | patch 0015：`COMMAND $<TARGET_FILE:cno_huffman_generator>` |
| 2 | `mysys/lf_hash.cc:852 std::bit_floor` 编译错 | **conan toolchain 的 cppstd=17 追加在上游 -std=c++20 之后生效 c++17**，`<bit>` 的 C++20 位函数全部不可见（本机实测 OHOS libc++ 本身有 bit_floor，`__cpp_lib_int_pow2=202002`；percona-server 8.4.10 用 `__builtin_clz` fallback 是因为其构建链同样无法保证 C++20） | 配方 `configure()` 中 `self.settings.rm_safe("compiler.cppstd")`（配方自管 std）+ `CMAKE_CXX_STANDARD=20`——根因消除法，无需源码补丁 |
| 3 | test_package test.c 编译错 | python 写文件时 `\n` 被解释为真实换行，字符串字面量断裂 | 重写 test.c 用字面拼接（工具链已修） |

## conan create 验证

- profile: /storage/Users/currentUser/.conan2/profiles/ohos-aarch64（pr:h 与 pr:b 同）
- 命令: `conan create . mysql-client-8.4/8.4.11 -pr:h=... -pr:b=... --build=missing`
- 产物: lib/libmysqlclient.a + include/mysql.h + bin/（mysql、mysqladmin、mysqldump、mysql_config 等 20 个客户端工具）
- test_package: consumer C 测试（mysql_library_init/end、版本 >= 80411、mysql_thread_safe、MYSQL handle init/close），VirtualRunEnv 注入运行期库路径后本机直接运行通过

## 工程环境备忘

- 源码下载用官方 CDN（本机 GitHub TLS 拦截不可达）；$TMPDIR=/data/storage/el2/base/temp 无 HMDFS 行尾 trim（python 写入不丢空格，与 OpenDesk 根目录行为不同）
- mysql-server 源码树解压两次（orig 基准 + work 修改树）后 difflib 生成补丁，git apply --check 对 orig 树全部通过
- 上游 libmysql_api_test 在 OHOS 被跳过（依赖 shared libmysql target），原因记录于 test_package/MANIFEST.yml
