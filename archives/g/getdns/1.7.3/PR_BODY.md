## PR 信息
- **三方库名称**：getdns（不含版本号）
- **上游版本**：1.7.3
- **上游仓库地址**：https://github.com/getdnsapi/getdns
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（新建知识草稿 DRAFT-13532：CMakeDeps PREFER_CONFIG vs 上游 Find 模块 target 失配，关联 E473）

> 源码包 URL（conandata.yml）: https://getdnsapi.net/releases/getdns-1-7-3/getdns-1.7.3.tar.gz （官方 dist tarball，含 src/jsmn 等 submodule；GitHub 自动 tag tarball 缺 submodule 无法构建，SHA-256 见 conandata.yml）

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 241 | Check 框架（src/test/，38 suite：232 个 .h 内联用例 + timeout/transport/timeout .c 内 9 个；BUILD_TESTING=ON 注册 4 个 ctest 目标） |
| 集成测试 | 6 | 手动测试程序（tests_stub_async/tests_stub_sync/tests_dict/tests_list/tests_namespaces，无 ctest 注册，开发者手动运行） |
| **合计** | **247** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 241 | 不变 | conan create build() 内真实运行 4 变体（check_getdns/check_getdns_event/check_getdns_ev/check_getdns_uv），实测 238/241 通过（98.75%） |
| 集成测试 | 6 | 不变 | 本地联网补跑全过（tests_stub_sync udp/tcp、tests_stub_async、tests_dict、tests_list、tests_namespaces rc=0） |
| **鸿蒙特有测试** | **6** | 新增 | test_package/src/getdns_smoke.c：__OHOS__ 平台宏探测 + getdns_context_create/destroy + dict set/get_bindata + get_names + pretty_print + getdns_get_version 实链验证（test_package 输出 platform: OpenHarmony/HarmonyOS） |
| **合计** | **253** | +6 | |

## 上游测试用例减少原因

无减少（单元测试 241/241 全注册执行，其中 3 个网络依赖用例因公网 DNS 污染环境限制未通过，见验证结果段逐项定性）。

## 上游测试用例修改说明
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在修改（逐条：文件路径+修改原因+修改内容）

## 补全测试用例说明
- [ ] **否**，上游已有测试覆盖
- [x] **是**，适配后补全（补全范围+原因+新增文件清单）
  - 新增 test_package/src/getdns_smoke.c（鸿蒙特有测试 6 项：__OHOS__ 宏、context 生命周期、dict bindata set/get、get_names、pretty_print、version API——上游 test_package 无 OHOS 平台验证，按 rule12 补全）

## 验证结果
- 编译状态：通过（conan create 全绿）
- 上游测试用例通过率：238/241（98.75%）
- 新增测试用例通过率：6/6（100%）

### 未通过用例逐项定性（3 项，全部为公网 DNS 污染环境限制）

| 用例 | 报错原文 | 定性与证据 |
|---|---|---|
| getdns_address_6 | `check_getdns_common.c:181: Unexpected value for "status": expecting ((ancount > 0) ? GETDNS_RETURN_GOOD : GETDNS_RETURN_NO_NAME): 901, but received: 900` | google.com A 查询经测试内嵌响应器（pthread+select 回环）转发系统 DNS 出口；本地实测 `nslookup google.com`（114.114.114.114）返回 185.45.5.35/2001::1（污染特征 IP，非 google 真实网段），断言失配。本地补跑证据：tests_stub_sync 以 TCP 通道查 www.google.com 得 GETDNS_RESPSTATUS_GOOD（rc=0），证明库本身解析功能正常，仅 UDP 出口 DNS 被污染 |
| getdns_general_9 | `check_getdns_common.c:221: Expected ancount >= 1, got 0` | 同上（google.com A 经响应器，污染 DNS 返回 ancount=0 应答） |
| getdns_general_sync_9 | `check_getdns_common.c:221: Expected ancount >= 1, got 0` | 同上 |

4 个 ctest 目标（test_noeventloop/test_libevent/test_libev/test_libuv）失败集完全一致（均为此 3 项），无 OHOS 平台特有失败。

### 编译验证
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: CMake（上游 cmake_minimum_required 3.20，传 CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容 cmake 4.x）
- 配置选项: -DENABLE_STUB_ONLY=ON（STUB 解析模式，省 libunbound 递归链）-DBUILD_GETDNS_QUERY=ON -DBUILD_GETDNS_SERVER_MON=ON -DBUILD_STUBBY=OFF -DBUILD_TESTING=ON -DBUILD_LIBEV=ON -DBUILD_LIBEVENT2=ON -DBUILD_LIBUV=ON

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | libgetdns.so/.a + libgetdns_ext_ev/event/uv.so/.a + bin/getdns_query + bin/getdns_server_mon |
| 产物存在性 | ✅ | conan create 验证（4 .a + 4 .so + 5 .h + getdns.pc） |
| ELF 格式 | ✅ | aarch64-unknown-linux-ohos（CI L4 门禁复检） |
| 运行测试 | ✅ | 单元 238/241 + 集成 6/6 + 鸿蒙冒烟 6/6 |

## 补丁说明
- patches/0001-FindLibuv-fix-LIBUV_LIBRARY-typo.patch：修复上游 cmake/modules/FindLibuv.cmake 笔误——`find_library(LIBUV_LIBRARIES ...)` 存入 LIBUV_LIBRARIES 但 guard 检查未定义的 `LIBUV_LIBRARY`，导致 Libuv::Libuv target 永不创建、getdns_ext_uv 链接失败（bugfix，一行）

## 依赖
- openssl/3.5.6（已发布）
- libidn2/2.3.8（已发布）
- check/0.15.2（已发布，测试框架）
- libev/4.33（已发布，事件循环扩展）
- libevent/2.1.13（已发布，事件循环扩展）
- libuv/1.52.1.1（已发布，事件循环扩展）

## 补充说明
- 版本号策略：1.7.3 为上游正式版本号
- 已知限制：3 个网络依赖测试用例受公网 DNS 污染影响（逐项定性见上，非 OHOS 平台缺陷）；ENABLE_STUB_ONLY=ON 模式不含递归解析（需递归场景由下游配置 unbound 上游解决）
- 知识草稿：knowledge/drafts/DRAFT-13532-getdns-1.7.3-cmakedeps-prefer-config-vs-upstream-find-modules.kv/.md（CMakeDeps PREFER_CONFIG 强制 ON 与上游自带 Find 模块 target 名失配的系统性解法：CMAKE_PROJECT_INCLUDE 注入，关联 E473 分支互补）
