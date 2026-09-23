# drogon 1.9.12 适配笔记

## 概述

drogon 是基于 C++17 的异步 HTTP Web 应用框架。本适配基于 ConanCenter 官方配方（drogon/all/conanfile.py，1.9.12 版本无上游补丁（沿用 1.9.13 的两个自有补丁，均已核对在 1.9.12 源码上逐字命中）），叠加 OHOS 平台适配。

## 关键决策

### 1. trantor 依赖策略（核在仓性）

- 任务指引：trantor 优先使用仓内已发布版本（核在仓性），缺则同 PR 携带/源码内嵌
- 仓内已有 trantor/1.5.26（已发布，drogon 1.9.12 的 submodule pin 是 v1.5.28）
- **兼容性核验**：diff trantor 1.5.26 vs 1.5.28——1.5.28 新增 `forwardToTLSBuffer()`/`getCloseCallback()`（TcpConnection.h），drogon 1.9.12 源码（lib/orm_lib/nosql_lib/drogon_ctl 全量 grep）**不引用任何新 API**，也不引用 1.5.26 已删除的 `verifySslName`。CCI 官方配方要求 `trantor/[>=1.5.25 <2]`，1.5.26 在范围内
- 结论：直接 `self.requires("trantor/1.5.26", transitive_headers=True, transitive_libs=True)` + `USE_SUBMODULE=OFF`

### 2. 依赖裁剪（非必需依赖全关）

drogon 上游把 postgres/mysql/sqlite/redis/brotli/yaml-cpp 全部做成 QUIET 软依赖（找不到自动跳过/编译 stub）。按任务指引全关：

```
BUILD_CTL=OFF            # drogon_ctl 命令行工具（依赖主机运行时）
BUILD_EXAMPLES=OFF
BUILD_DOC=OFF
BUILD_POSTGRESQL=OFF
BUILD_MYSQL=OFF
BUILD_SQLITE=OFF
BUILD_REDIS=OFF
BUILD_BROTLI=OFF
BUILD_YAML_CONFIG=OFF
BUILD_TESTING=ON         # 上游 DROGON_TEST 套件
USE_SUBMODULE=OFF
```

保留 `BUILD_ORM=ON`（ORM 头文件/核心是 drogon 公共 API 一部分，关闭会缺 drogon/orm/*.h）。

### 3. UUID 依赖（坑 1）

- drogon `lib/src/Utilities.cc` 用 `#include <uuid.h>` + `uuid_generate()`（util-linux libuuid 语义）
- 仓内 uuid/2.40.1（util-linux）头文件在 `include/uuid/uuid.h`，drogon 源码用 ossp 风格平铺 `<uuid.h>`
- CMakeDeps 映射：`uuid -> cmake_file_name=UUID, cmake_target_name=UUID_lib`（满足 drogon 自带 FindUUID.cmake 的 try_compile 探测）
- **补丁 0001**：`<uuid.h>` → `<uuid/uuid.h>`（Utilities.cc + normal_uuid_lib_test.cc）。CCI 的 util-linux-libuuid 是靠 `includedirs.append("include/uuid")` 双布局解决的，我们仓内 uuid 包没做，配平方侧 patch 解决

### 4. 上游测试相对路径 bug（坑 2）

- `lib/tests/unittests/FileTypeTest.cc:1` 用 `#include "../lib/src/HttpUtils.h"`，从 `lib/tests/unittests/` 出发只到 `lib/tests/lib/src/`（不存在）
- 同目录其他测试全部用 `../../lib/src/...`——上游笔误，非 MSVC 分支必然编译失败
- **补丁 0002**：修正为 `../../lib/src/HttpUtils.h`

### 5. CookieSameSite 证书（坑 3）

- 上游 test.sh 从 trantor submodule 拷 `server.crt/server.key` 到测试运行目录；USE_SUBMODULE=OFF 时无源可拷
- 测试二进制在 ctest 工作目录（`build/Release/lib/tests/`，即 add_test 所在 CMakeLists 目录）加载证书
- 方案：`exports_sources = "resources/*"` 携带 trantor 1.5.28 源码树里的同名测试证书，build() 跑 ctest 前拷到 `lib/tests/`

### 6. OHOS 运行时环境两连坑（坑 4/5）

- **mksh 加载失败**：`/system/bin/sh` 无法加载动态链接的测试二进制（aa3d 先例）→ ctest 用 `CONFIG_SHELL`（/data/service/hnp/bin/bash）包裹执行
- **libc++_shared.so 错配**：本机（OpenDesk 环境进程）LD_LIBRARY_PATH 带 `/data/storage/el1/bundle/libs/arm64`，其中有**不兼容的 libc++_shared.so**（缺 `codecvt_utf8` 等符号）→ loader 按路径序先命中它，测试全部 "Error relocating"
- 修复：`generate()` 里 `Environment().prepend_path("LD_LIBRARY_PATH", <toolchain libc++ dir>)` + `save_script`，conanrun 自动加载；libc++ 目录从 `os.path.realpath(compiler)` 推导（hnp/bin/clang++ 是指向 ohos-sdk 的软链，不 resolve 会推导失败）
- jsoncpp 包 CI 先例只 `VirtualRunEnv(self).generate()`——远端 worker 环境干净无此问题；本机开发环境必须有前置保护

### 7. 测试统计口径

- 上游 CMake `ParseAndAddDrogonTests` 扫描 `DROGON_TEST` 宏逐个注册 ctest 用例。取数：`grep -hcE "^DROGON_TEST\(" lib/tests/unittests/*.cc` = 45，`lib/tests/*.cc` = 2（CookieSameSite、RealIpResolverTest），合计 47 个宏
- 其中 `CoroutineTest.cc` 的 7 个需 `DROGON_CXX_STANDARD >= 20 AND HAS_COROUTINE`、`BrotliTest.cc` 的 1 个需 `Brotli_FOUND`，本构建（`cppstd=17` + `BUILD_BROTLI=OFF`）不注册 → 实际注册 **39** = unittest 37 + cookie_same_site 1 + real_ip_resolver 1
- 真机实测（ohos-aarch64，两个 profile 同指设备）：`100% tests passed, 0 tests failed out of 39`
- `orm_lib/tests` 的 5 个 DB 测试目标（db_test/pipeline_test/db_listener_test/conn_options_test/db_api_test）上游不注册 `add_test`（`grep -rn "add_test(" --include=CMakeLists.txt .` 除 ParseAndAddDrogonTests 外 0 命中），且 DB 客户端已裁剪，不计入运行数；`lib/tests/integration_test/` 在 1.9.12 没有 CMakeLists，不参与构建——与 ConanCenter 官方默认（`BUILD_CTL=False`）同口径
- 与 1.9.13 的差异：仓内已合入的 1.9.13 同口径注册 48，本版本注册 39，差额来自上游两个版本 `lib/tests/` 用例集合本身的增减，不是本配方裁剪造成的（裁剪项两版完全一致）

## 验证结果

- conan create（`-pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`）：PASS
- 上游测试：39/39 PASS（DROGON_TEST 框架，ctest 注册口径）
- test_package（drogon 核心子系统链接+运行：HttpAppFramework/EventLoop、HttpResponse、路由注册、Base64、HttpClient 工厂）：1/1 PASS
