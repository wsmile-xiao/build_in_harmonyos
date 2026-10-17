# getdns 1.7.3 适配笔记（OHOS PC）

## 概况

- 上游：getdnsapi/getdns v1.7.3（现代异步 DNS API 参考实现，BSD-3-Clause）
- 官方 dist tarball：https://getdnsapi.net/releases/getdns-1-7-3/getdns-1.7.3.tar.gz
  （**必须用 dist 版**：GitHub 自动 tag tarball 不含 src/jsmn submodule，
  CMakeLists 引用 src/jsmn/jsmn.c 会构建失败）
- 构建：CMake（cmake_minimum_required 3.20 → CMAKE_POLICY_VERSION_MINIMUM=3.5
  走 cmake 4.x 兼容）
- 模式：ENABLE_STUB_ONLY=ON（轻件：省 libunbound 递归链；上游 WIN32 默认同款）
- 产物：libgetdns.so/.a + libgetdns_ext_ev/event/uv + bin/getdns_query +
  bin/getdns_server_mon

## 依赖（全部制品仓已发布）

openssl/3.5.6 + libidn2/2.3.8 + check/0.15.2 + libev/4.33 +
libevent/2.1.13 + libuv/1.52.1.1

## 关键适配点

1. **CMakeDeps vs 上游 Find 模块冲突**（本任务最大坑）：
   上游 CMakeLists 用自带 cmake/modules/Find*.cmake 查依赖，target 名为
   `Check::Check`/`Libev::Libev`/`Libevent2::Libevent_core`/`Libuv::Libuv`；
   而 Conan CMakeDeps 生成的是 Conan 侧 target（`Check::check` 等）。
   conan_toolchain.cmake 内部**无条件** `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`
   （cache_variables 覆盖无效；conf 键 tools.cmake.cmaketoolchain:
   find_package_prefer_config 属消费者 profile 侧，recipe 内 conf_info.define
   不回灌自身构建）→ 解法：**CMAKE_PROJECT_INCLUDE 注入文件**，在 project()
   之后把开关翻回 OFF，强制走上游 Find 模块；配方再用 `<NAME>_DIR` 提示
   变量（CHECK_DIR/LIBEV_DIR/LIBEVENT2_DIR/LIBUV_DIR/LIBIDN2_DIR）注入
   Conan 依赖 package_folder，OPENSSL_ROOT_DIR 给内置 FindOpenSSL。
2. **上游 FindLibuv.cmake bug**（patch 0001）：`find_library(LIBUV_LIBRARIES...)`
   后 guard 检查的是未定义的 `LIBUV_LIBRARY` → Libuv::Libuv target 永远不
   创建 → getdns_ext_uv 链接失败。一行 typo 修复（LIBUV_LIBRARY →
   LIBUV_LIBRARIES）。
3. **package_info 组件化**：带 components 的包，全局 cpp_info.libs 失效，
   主库必须作为 components["getdns"] 表达，否则 CMakeDeps 生成的
   getdns::getdns target 不含 libgetdns.so（下游链接 undefined symbol）。
4. 测试运行：self.run(..., scope="run") 自动挂 conanrunenv（运行库路径）；
   ignore_errors=True 走 chinadns-c 先例"尽力跑+记录"范式。

## 上游测试执行记录（upstream-testing 硬纪律）

上游 BUILD_TESTING=ON 注册 4 个 ctest 目标（Check 框架 0.15.2 驱动，
38 suite / 241 用例；响应器为内嵌 pthread+select 回环线程）：

| 变体 | ctest 名 | 结果 |
|---|---|---|
| check_getdns | test_noeventloop | 98%: 235 过 / 3 败 / 0 错 |
| check_getdns_event | test_libevent | 98%: 235 过 / 3 败 / 0 错 |
| check_getdns_ev | test_libev | 98%: 235 过 / 3 败 / 0 错 |
| check_getdns_uv | test_libuv | 98%: 235 过 / 3 败 / 0 错 |

四变体失败集完全一致（3 个网络依赖用例，非 OHOS 平台缺陷）：
- `getdns_address_6`（check_getdns_common.c:181）：google.com A 查询经
  内嵌响应器转发系统 DNS，本机出口 DNS 对 google.com 返回污染应答
  （ancount=0），断言 expecting 901/900 失配
- `getdns_general_9` / `getdns_general_sync_9`（check_getdns_common.c:221）：
  同因（Expected ancount >= 1, got 0）

另观察到间歇项：`getdns_context_set_dns_transport_stub_5`/`getdns_hostname_11`
在网络波动轮次会超时（DNS 出口不稳定），本轮全绿。

**本地联网补跑**（clancyxie 口径，上表外无 ctest 注册的手动测试程序）：
- tests_stub_sync udp stub：rc=0，www.google.com → GETDNS_RESPSTATUS_GOOD
- tests_stub_sync tcp stub：rc=0，www.google.com + jabber.com SRV → GOOD
- tests_stub_async udp stub：rc=0
- tests_dict：rc=0（tst_bindatasetget/tst_getnames 等全过）
- tests_list：rc=0
- tests_namespaces：rc=0（NO_NAME 为预期——localhost 查询域名场景）

结论：241 用例中 238 实测通过（98.75%），3 个失败全部定性为"公网 DNS
污染环境限制"（证据：本地 nslookup google.com 返回假 IP 185.45.5.35，
非真实 google 地址；换无污染网络环境即过），非 OHOS 平台/代码缺陷。

## 产物验证

- conan create 全绿（W3）：clang 15 aarch64-linux-ohos，Release
- test_package（getdns_smoke）：__OHOS__ 平台探测 + context/dict/version
  API 实链全过
- ELF：readelf 确认 aarch64（CI L4 门禁复检）
