# libhttpserver 0.19.0 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libhttpserver（libmicrohttpd 的 C++ 封装） |
| 版本 | 0.19.0（任务指定 2.0.0 → 判定 env_unsupported，降级到 0.19.0，见下） |
| 状态 | built |
| 构建系统 | autotools（tarball 无 configure，需 autoreconf -fi） |
| 源码 | https://github.com/etr/libhttpserver/archive/refs/tags/0.19.0.tar.gz |
| sha256 | b108769ed68d72c58961c517ab16c3a64e4efdc4c45687723bb45bb9e04c5193 |

## 2.0.0 → 0.19.0 版本决策（env_unsupported 证据链）
- 指定上游 tag 2.0.0 要求 `AX_CXX_COMPILE_STDCXX([20], [noext], [mandatory])`，核心实现
  使用 `std::pmr::` 36 处（http_request_impl / http_request_impl_args / connection_state 等
  arena 分配器架构是 2.0.0 的核心设计）。
- OHOS 工具链 libc++ 15004（clang 15，CI 与本地同款 profile cppstd 17）**没有标准
  `<memory_resource>` 头**（只有 experimental/memory_resource）：
  `echo '#include <memory_resource>' | clang++ -std=c++20 -x c++ - -fsyntax-only`
  → `fatal error: 'memory_resource' file not found`（SDK llvm/include/c++/v1 实查）。
- 改掉 pmr = 重写上游核心数据结构，违反最小 patch 原则 → 2.0.0 判 env_unsupported。
- 0.19.0（上一代正式 release）：C++17、无 pmr 引用（grep 实证 0 处），本机交叉
  configure+make 全通过。

## 适配要点
1. **bootstrap**：release tarball 不带 configure，build() 先 `autoreconf -fi`
   （tool_requires automake/1.18 + libtool/2.5.4，abiword-plugin-clarisworks 先例）。
2. **交叉 triplet**：--build=x86_64-unknown-linux-gnu --host=aarch64-linux-ohos
   （config.sub 原生支持 ohos）。configure 的 cross 分支（host≠build）会跳过
   MHD 运行时版本探测（只查编译），行为正确。
3. **AC_CHECK 预置**：AC_CHECK_HEADER(microhttpd.h)/AC_CHECK_LIB(microhttpd,
   MHD_start_daemon) 交叉下不可执行——env 预置 ac_cv_header_microhttpd_h=yes +
   ac_cv_lib_microhttpd_MHD_start_daemon=yes，CPPFLAGS/LDFLAGS 指 conan 包路径。
4. **-lstdc++ 补丁**：configure.ac 的 AM_LDFLAGS="-lstdc++" 硬编码在 OHOS（libc++）
   链接失败 ld.lld: unable to find library -lstdc++ → patch 0001 加 linux-ohos* 分支
   置空（同上游 freebsd 分支先例，非平台宏，纯构建系统分支）。
5. **E011 umask**：生成后的 configure 内 umask 077 → 022（HMDFS config.status 临时目录
   不可写；CI Linux 上幂等无害）。
6. **make -j4**：HMDFS jobserver fifo 限制下保守并行。

## 上游测试
- 上游 test/unit + test/integ 合并为 12 个 littletest 可执行（check_PROGRAMS），共 152 tests / 811 checks。
- **本地真实执行结果：152 tests，808 checks 通过，3 checks 失败（豁免）**：
  | 程序 | tests | checks过/总 |
  |------|-------|------------|
  | basic | 40 | 174/174 |
  | file_upload | 10 | 133/133 |
  | http_utils | 45 | 279/279 |
  | threaded | 1 | 2/2 |
  | nodelay | 1 | 2/2 |
  | string_utilities | 6 | 8/8 |
  | http_endpoint | 23 | 129/129 |
  | ban_system | 2 | 11/11 |
  | ws_start_stop | 15 | 48/51（3 SSL 失败） |
  | authentication | 4 | 12/12 |
  | deferred | 2 | 6/6 |
  | http_resource | 3 | 4/4 |
- **3 例豁免**：ws_start_stop 的 ssl_base/ssl_with_protocol_priorities/ssl_with_trust——
  依赖 libmicrohttpd/1.0.1 制品包构建时未启用 HTTPS（gnutls 关闭），MHD HTTPS daemon
  起不来（`Unable to connect daemon to port: 8080`），属依赖包能力边界，非本包缺陷；
  本包 HTTP 链路 149/149 全过。
- test_package 以最小真实 HTTP 往返（起服务→GET→比对→停）覆盖核心链路（6 断言全过）。
- 上游测试代码未修改。

## 依赖
- libmicrohttpd/1.0.1（已发布制品仓 ✅，MHD_VERSION 0x01000100 ≥ 0x01000000）
- 构建期：automake/1.18、libtool/2.5.4（已发布 ✅）
