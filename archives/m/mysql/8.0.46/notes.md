# mysql 8.0.46 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMake 单仓，client-only 子集）
- 编译日期: 2026-09-03
- 编译器: OHOS clang（aarch64-linux-ohos，宿主鸿蒙 PC）
- 状态: published
- 依赖（Conan 制品仓全部命中缓存二进制）: openssl/3.5.6.1.1、zlib/1.3.1、ncurses/6.4、boost/1.84.0
- 参照: knowledge E459（percona-server 8.4.10_10 OHOS 适配）+ archives/p/percona-server/8.4.10_10

## 版本选择

mysql-8.0 系列上游最新 GA：8.0.46（GitHub 官方仓 tag `mysql-8.0.46`）。发布 tarball 主源为官方 CDN（cdn.mysql.com，与 dev.mysql.com 同源），GitHub tag 归档为备源。
源码 sha256 = e0d1a98ae5188c6a4efed74c74ff28115d4b791bc9d591a78e14d20aded67344（官方发布 tarball；GitHub tag 归档为不同压缩流，sha256 不同，二者源码树一致，15 个补丁均验证兼容）。

## 编译步骤（探索式，从 .work 构建树复现）

1. conan install 四个依赖到本地缓存，取各包 package_folder 路径。
2. cmake 配置（关键开关见 manifest.yaml configure_options；构建目录 `build2`）。
3. `make -j6`（约 6 分钟，client-only 子集，峰值内存约 2.5G）。
4. `make install` 到 staging（bin/ 20 个客户端工具 + lib/libmysqlclient.a + include/）。
5. 产物验证：`readelf -h bin/mysql` → ELF64 / AArch64 / DYN(PIE)；NEEDED 仅 libc++_shared.so 与 libc.so。

## 配置迭代记录（关键 10 轮）

| 轮次 | 卡点 | 根因 | 解决 |
|---|---|---|---|
| 1-2 | boost 1.77 检查 FATAL | WITH_BOOST 给了 conan 包根目录，boost.cmake 用 FIND_PATH 直接找 boost/version.hpp | WITH_BOOST 指向 `<pkg>/include`；另将 boost.cmake 的 minor==77 检查放宽为 LESS 77（patch 0001） |
| 3 | libmysql CMakeLists:276 DNS SRV 报错 | MYSQL_CHECK_RPC/resolver 探测路径不适用 OHOS | 顶层 `IF(LINUX AND NOT OHOS)` 跳过 MYSQL_CHECK_RPC；libmysql DNS SRV 检测加 OHOS 分支（HAVE_UNIX_DNS_SRV=1，不链 libresolv，patch 0001/0002） |
| 4 | `Can't find neither Win32 nor Unix DNS SRV APIs` | cmake 变量 OHOS 未定义（探索期） | 命令行加 `-DOHOS=1`（Percona 配方同款 cache_variables） |
| 5 | client/CMakeLists:230 TARGET_COMPILE_OPTIONS 报错 | shared json_binlog target 被跳过后残留引用 | json_binlog/json_binlog_main 及其 warning 选项块全部加 `IF(NOT OHOS)`/`IF(TARGET ...)` 守卫 |
| 6 | scripts/CMakeLists:372 GET_TARGET_PROPERTY 报错 | shared libmysql target 不存在 | OHOS 分支回退用 mysqlclient 的 VERSION/OUTPUT_NAME |
| 7 | `System is unknown to cmake`；CMAKE_CXX_FLAGS 仅 `-fPIC -O2`，icu 以 C++14 编译报 std::is_same_v 错误 | **CMAKE_SYSTEM_NAME=HarmonyOS 是 CMake 未知系统名 → UNIX=0 → compiler_options.cmake 的整个 IF(UNIX) 块（含 -std=c++17）被跳过** | 改用 `-DCMAKE_SYSTEM_NAME=Linux`（Percona 配方同款），OHOS 特性用 OHOS 变量 + patch 门控 |
| 8 | 6 处 `try_run() invoked in cross-compiling mode` | 显式设置 CMAKE_SYSTEM_NAME 即强制交叉模式，try_run 无结果 | 预置 HAVE_SETNS_EXITCODE=1、HAVE_CLOCK_GETTIME_EXITCODE=0、HAVE_CLOCK_REALTIME_EXITCODE=0、HAVE_FALLOC_PUNCH_HOLE_AND_KEEP_SIZE_EXITCODE=0、HAVE___BUILTIN_FFS_EXITCODE=0、TEST_RUN_RESULT=0(+__TRYRUN_OUTPUT=2.1.11-stable) |
| 9 | libevent.cmake:181 版本断言失败 | bundled libevent 版本探测也是 try_run | 同上 TEST_RUN_RESULT 预置 |
| 10 | rpcgen.cmake:114 `Could not find rpcgen` | group_replication/libmysqlgcs 的 XDR 生成需要 rpcgen | rpcgen.cmake 条件 `IF(NOT LINUX)` → `IF(NOT LINUX OR OHOS)` 走 Windows 同款 vanilla 预生成文件路径（后因 WITHOUT_SERVER=ON 实际不编译，保留以保完整性） |
| 终 | group_replication、storage/ndb、GenError(comp_err) 全在编译 | **漏传 -DWITHOUT_SERVER=ON** | 补上后配置收敛，构建范围缩至客户端子集 |

## 编译期问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | mysys/my_thread.cc:143 `pthread_cancel` 未声明 | OHOS libc 不提供 pthread_cancel | `my_thread_cancel()` 在 OHOS 下 `errno=ENOSYS; return -1`（Percona 8.4.10 同款语义，patch 0002；宏 OHOS_PTHREAD_CANCEL_UNSUPPORTED 由顶层 ADD_DEFINITIONS 注入） |
| 2 | GenError 目标 Error 127 | `IF(NOT CMAKE_CROSSCOMPILING)` 使 comp_err 不构建，但 GenError 自定义命令仍引用 | patch 0001: 条件放宽 `OR OHOS`（OHOS 二进制生成器可在鸿蒙 PC 宿主直接运行），命令统一 `$<TARGET_FILE:comp_err>` 并补 target 依赖；comp_client_err/comp_sql/uca9dump 同样 TARGET_FILE 化 |
| 3 | sql-common/get_password.cc `no matching function for call to 'my_read'` | uchar* 显式转换缺失（HMDFS 缓存导致该修改一度未生效，实为已应用状态） | `(uchar *)&tmp` 强转（Percona 同款，patch 0002） |

## 源码修改（patches/）

### 0001-ohos-client-build-system.patch（构建系统，10 个文件）

- 顶层 `CMakeLists.txt`：`IF(LINUX AND NOT OHOS)` 跳过 MYSQL_CHECK_RPC；OHOS 时 ADD_DEFINITIONS(-DOHOS_LIBC_DNS_SRV -DOHOS_PTHREAD_CANCEL_UNSUPPORTED)
- `cmake/boost.cmake`：bundled Boost minor 检查 `EQUAL 77` → `LESS 77`（接受制品仓 1.84.0；上游下载逻辑不动）
- `libmysql/CMakeLists.txt`：DNS SRV 检测 OHOS 分支；MERGE_LIBRARIES_SHARED(libmysql) 与 libmysql_api_test→run_libmysql_api_test 段落 `IF(NOT OHOS)` 守卫；LINK_FLAG_Z_DEFS/version-script/CLEAN_DIRECT_OUTPUT 加 `TARGET libmysql` 守卫（HMDFS symlink 陷阱，E459）
- `client/CMakeLists.txt`：shared json_binlog、json_binlog_main 及 warning 选项块守卫
- `scripts/CMakeLists.txt` / `scripts/sys_schema/CMakeLists.txt` / `strings/CMakeLists.txt`：comp_sql/uca9dump 命令改 `$<TARGET_FILE:...>` 绝对路径（E459 构建工具规范）
- `utilities/CMakeLists.txt`：comp_err 构建条件 `OR OHOS` + TARGET_FILE + target 依赖
- `extra/libedit/.../src/CMakeLists.txt`：edit target 定义 OHOS_LIBEDIT_TERMCAP
- `plugin/group_replication/libmysqlgcs/cmake/rpcgen.cmake`：无 rpcgen 时走 vanilla 分支

### 0002-ohos-libc-compat.patch（libc 兼容，5 个文件）

- `libmysql/dns_srv.cc`：3 处 `#ifdef LINUX_ALPINE` → `#if defined(LINUX_ALPINE) || defined(OHOS_LIBC_DNS_SRV)`（OHOS libc 自带 res_init/res_search，无 libresolv）
- `mysys/my_thread.cc`：my_thread_cancel 的 pthread_cancel fallback
- `sql-common/get_password.cc`：`(uchar *)` 强转
- `extra/libedit/.../chartype.h`：4 字节 wchar_t 平台（OHOS）纳入支持列表
- `extra/libedit/.../terminal.c`：termcap 手动原型 fallback（OHOS_LIBEDIT_TERMCAP）

## 测试

- test_package：消费者 C 测试程序（mysql_library_init/end、mysql_get_client_info/version >= 80446、mysql_thread_safe、MYSQL handle init/close），链接 mysql::mysql（静态 libmysqlclient.a）。
- 上游 libmysql_api_test 在 OHOS 被跳过（依赖 shared libmysql target，见 patch 0001），原因记录于 test_package/MANIFEST.yml。

## 工程环境备忘（对本仓后续适配有用）

- **HMDFS 写入层会剥离文本文件行尾空格**：tar 命令解压保留原始字节；python（tarfile/直接写）与 filemgr 编辑工具写入会 trim 行尾空格。生成 .patch 必须以 tar 命令解压的干净树为基准（.work 树被 trim 后 diff 会混入大量噪音 hunk 且无法应用到上游源码）。~/.conan2 目录无此问题。
- `/tmp` 只读（E002），临时目录用 `$HOME/tmp`。
- 语言预检（R47）误判为 python 的根因：lang_detect 的 _SKIP_DIRS 不含 bundled `extra/`，扫到 `extra/protobuf/protobuf-24.4/python/setup.py`；且 bundled protobuf 的 java/python 文件把 cpp 占比稀释到 69.4%（<70% 阈值）。只读诊断（tmp/diag_lang_mysql.py）证实排除 bundled extra/ 后 MySQL 实为 cpp 84.3% + CMake，是纯 C/C++ 项目，如实记录后继续。
- GitHub 源码下载在本机需用 `curl -fL`（Python urllib SSL 证书链问题）。
---

**编译结束**: 2026-09-03 22:21
**最终状态**: published
