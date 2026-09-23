# xrootd 5.8.1 适配笔记（OpenHarmony PC / aarch64）

- 日期: 2026-09-18
- Agent: 7B27
- 上游: https://github.com/xrootd/xrootd (v5.8.1)
- 构建系统: CMake (>= 3.16)
- 语言: C++17 (lang-preflight: cpp)

## 上游测试清点（R51）

| 套件 | 目录 | 状态 |
|---|---|---|
| XrdCl 单元测试 | tests/XrdCl (URL/Poller/Socket/Utils) | ✅ 构建+运行 |
| XrdOuc 单元测试 | tests/XrdOucTests | ✅ 构建+运行 |
| XrdTpc 单元测试 | tests/XrdTpcTests | ✅ 构建+运行 |
| XrdPfc 单元测试 | tests/XrdPfcTests | ✅ 构建+运行 |
| XrdHttp 单元测试 | tests/XrdHttpTests | ✅ 构建+运行（13 项：checksumHandler 2 + ReadRange 11） |
| XrdSsi 单元测试 | tests/XrdSsiTests | ✅ 构建（无独立 gtest 注册项） |
| XrdCeph / XrdEc / scitokens | — | ⛔ 未构建（依赖 ceph/isal/scitokens 未发布，上游默认关闭） |
| XRootD/cluster/stress/TPCTests 集成测试 | tests/* | ⛔ 未运行：需多节点集群编排 harness（ENABLE_SERVER_TESTS），非单机可执行 |

**实测结果（真机 OHOS 设备）**：`ctest` **30/30 通过（100%）**，总时长 65.4s。
**端到端验证**：xrootd 服务器（端口 1094）+ xrdcp 上传/下载（54B 文本 + 10MB 二进制）内容逐字节校验一致；xrdfs ls/stat 正常。

## 依赖（全部来自 ohpcd 制品仓）

| 依赖 | 版本 | 用途 |
|---|---|---|
| zlib | 1.3.1.1 | 压缩（必需）|
| openssl | 3.5.6.1.2 | 加密/TLS（必需，>= 1.0.2）|
| libuuid | 2.40.4 | UUID（必需）|
| readline | 8.3 | xrdfs/frm_admin 交互 shell |
| ncurses | 6.6 | 静态 readline 的 terminfo 符号（宽字符版 libncursesw.a） |
| libxml2 | 2.15.3.1 | XrdXml XML2 reader（监控）|
| libcurl | 8.5.0 | HTTP TPC 三方复制插件 |
| gtest | 1.17.0.1 | 上游单元测试（test_requires）|

注：zlib 固定 1.3.1.1（与 libcurl 8.5.0 的依赖图对齐，1.3.1.2 会版本冲突）。

## 上游组件开关（"if possible" 语义）

已启用：XrdCl 客户端、XrdServer 服务器、全部管理工具、XrdSec 全家（unix/gsi/pwd/sss/ztn）、
HTTP 服务器、HTTP TPC（curl）、POSIX 前端（libXrdPosix + Preload）、PFC 缓存、readline、libxml2、
CMS、FRM、监控、XrdXml(bundled tinyxml + libxml2 reader)。

未启用（对应三方库未发布到制品仓，上游 CMake 在依赖缺失时自动关闭，未做源码裁剪）：
- Kerberos5（无 krb5 包）
- VOMS / Macaroons / SciTokens（无包；macaroons 还需 json-c）
- XrdEc 纠删码（需 isal）
- XrdClHttp（需 Davix）
- Ceph（需 librados）
- systemd 集成（无 systemd）
- FUSE（上游 CMake 限制 `CMAKE_SYSTEM_NAME MATCHES "Linux|kFreeBSD"`，HarmonyOS 不匹配且 OHOS 无 /dev/fuse）
- Python 绑定（交叉环境无目标 Python Development）

## 平台适配点（源码 patch，见 patches/）

1. **rindex/index → strrchr/strchr**（~60 文件 ~130 处）：OHOS musl 的 strings.h 不声明 rindex，
   libc 无该符号。sed 批量替换为 POSIX 等价函数，语义完全一致。

2. **pthread_cancel 系列 → SIGUSR2 信号重建 deferred cancellation**
   （src/XrdSys/XrdSysPthread.hh/.cc、src/XrdCl/XrdClJobManager.cc、XrdClTaskManager.cc，E513 方案）：
   OHOS musl 完全没有线程取消 API。实现：
   - `Cancel()/Kill()` = `pthread_kill(tid, SIGUSR2)`，SIGUSR2 处理器在目标线程内 `pthread_exit(0)`
   - 线程局部变量 `ohosNoCancel/ohosPending` 复刻 deferred 语义：禁用期间信号置 pending，
     `SetCancelOn()` 或 `CancelPoint()` 时补触发
   - **信号选择实证**：RT 信号（SIGRTMIN）经 pthread_kill 在 OHOS 上返回 0 但永不送达（最小
     复现程序验证）；SIGUSR1 被 xrootd 自身占用（XrdClLocalFileHandler AIO/XrdFfs）；SIGUSR2 仅
     被 XrdOssAio 的无 RT 信号回退分支引用（该分支编译期不激活且 AIO 已整体禁用）→ 选 SIGUSR2
   - XrdCl 两个管理器（JobManager/TaskManager）原始 pthread_* 调用改走 XrdSysThread 封装
   - 验证：TaskManagerTest（Stop=Cancel+Join 路径）通过；30/30 全绿

3. **linux/tcp.h → netinet/tcp.h**（XrdNetPMarkFF.cc）：musl 下 linux/socket.h 会重复定义
   sockaddr_storage；musl 的 netinet/tcp.h 完整提供 tcp_info/TCP_INFO。

4. **innetgr 缺失**（XrdNetSecurity.cc、XrdAccGroups.cc）：上游已有 `#ifdef MUSL` 的
   return 0 stub，扩展条件到 `__OHOS__`（上游 musl 语义：netgroup 检查恒失败）。

5. **getpass 缺失**（XrdSutAux.cc）：termios 实现（/dev/tty + 关回显），与 glibc 行为一致，
   供 XrdSecpwd 管理工具交互输密。

6. **getspnam 缺失**（cmake/XRootDSystemCheck.cmake）：OHOS shadow.h 是空壳（有文件无声明）。
   在 CMake 检测中追加 `check_function_exists(getspnam)`，HAVE_SHADOWPW 正确置 false，
   走普通 passwd 路径。

7. **POSIX AIO 缺失**（XrdOssAio.cc、XrdClLocalFileHandler.cc、XrdSfsAio.hh 相关）：
   OHOS 的 aio.h 只有 struct 定义无函数、libc 无符号，但 unistd.h 谎报 _POSIX_ASYNCHRONOUS_IO。
   按上游 macOS 先例 `#undef _POSIX_ASYNCHRONOUS_IO`，激活上游自带的同步 I/O 回退路径
   （XrdOssAio 每函数有同步 fallback；XrdClLocalFileHandler 四个 op 走 pread/pwrite/fdatasync，
   与 macOS 同路径）。XrdClLocalFileHandler 的 AioCtx（含 aio_return/aio_error）整体
   `#if !defined(__OHOS__)` 守卫。

8. **typeof → decltype**（XrdOssStatsConfig.cc 7 处）：OHOS clang -std=c++17 严格模式拒绝
   GNU typeof 扩展（__typeof__ 仍可用，XrdOucJson.hh 的 nlohmann 宏不受影响）。

9. **fseterr**（XrdPosix.cc）：OHOS musl 提供 __fseterr（stdio_ext.h），扩展上游 MUSL 分支
   到 `__OHOS__`。

10. **XrdPosixPreload *64 宏别名**（XrdPosixPreload.cc）：musl 将 open64 等宏别名到 open，
    导致 preload 封装重复定义。扩展上游 `#ifdef MUSL` 的 #undef 块到 `__OHOS__`。

11. **FIFO/unix socket 文件创建被禁**（XrdOfsEvr.cc、XrdXrootdConfig.cc、XrdXrootdAdmin.cc）：
    OHOS 全文件系统 mkfifo 返回 EPERM，AF_UNIX 路径套接字 bind 同样被拒（实测；抽象命名空间
    套接字可用但改传输层过于侵入）。这两处是辅助管理通道（ofsEvents FIFO、admin socket），
    改为**优雅降级**：警告并继续运行，核心文件服务不受影响。端到端验证已证实。

12. **tests/XrdTpcTests/CMakeLists.txt**：XrdTpcUtils 目标缺 CURL 链接（curl 头文件不在默认
    搜索路径时暴露），补 `target_link_libraries(XrdTpcUtils PUBLIC CURL::libcurl)`。

## 配方层适配（conanfile.py，非源码 patch）

1. **SONAME flags**（E383）：`CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG = "-Wl,-soname,"`
   ——CMake 无 Platform/HarmonyOS 模块导致该变量为空，库无 SONAME 时 lld 把相对路径
   写进 DT_NEEDED（../libXrdUtils.so，运行时找不到）。

2. **readline 注入**：xrootd 的 FindReadline.cmake 因 `PATH_SUFFIXES lib` 与 conan
   CMAKE_LIBRARY_PATH（已以 /lib 结尾）不兼容找不到库；且其检查大写 READLINE_FOUND 而
   config 模式设置 Readline_FOUND。通过 CMake 变量注入
   `READLINE_FOUND/READLINE_LIBRARY/NCURSES_LIBRARY/READLINE_INCLUDE_DIR`
   （ncurses 为宽字符版 libncursesw.a）。xrdfs 交互 shell 已实测（readline 初始化正常）。

3. **GTest shim**（CMAKE_PROJECT_INCLUDE）：conan gtest 提供 GTest::gtest/GTest::gtest_main
   组件目标，xrootd 测试链接 GTest::GTest/GTest::Main（FindGTest 模块命名）；shim 创建
   INTERFACE IMPORTED 别名 + 置 GTEST_FOUND。

4. **构建选项**：ENABLE_PYTHON=OFF（交叉无目标 Python）、ENABLE_TESTS=ON、
   ENABLE_SERVER_TESTS=OFF（集群 harness 单机不可跑）、curl_multi_wait 检测失败走上游
   select() 回退（功能完整）。

## 遗留事项

- tests 的 gtest_discover 需要构建期 LD_LIBRARY_PATH 包含构建树 src/ 与 tests/common/
  及 libcurl 包目录（配方 build() 内已处理）。
- XrdFfs(xrootdfs) 二进制已构建但 OHOS 无 /dev/fuse，实际不可挂载（上游限制，非裁剪）。
---

**编译结束**: 2026-09-18 20:35
**最终状态**: built
