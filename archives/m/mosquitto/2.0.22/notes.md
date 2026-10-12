# mosquitto 2.0.22 — 编译进度

> 档案创建时间: 2026-10-08
> 最后更新: 2026-10-08
> 状态: built (本地 conan create 全绿, 待 CI 验证)

## 一、基本信息
| 项目 | 值 |
|------|------|
| 软件 | mosquitto |
| 版本 | 2.0.22 |
| 状态 | ✅ success |
| 构建系统 | cmake |
| 源码路径 | https://mosquitto.org/files/source/mosquitto-2.0.22.tar.gz |
| 性质 | 升级件（main 已有 2.0.18，本次升级到 2.0.22） |

## 二、编译阶段

### Phase 1: 环境准备
- [x] init-build 完成 / 源码下载解压（官方 tarball + sha256 核验）

### Phase 2: 编译（cmake + make）
- [x] cmake configure 完成
- [x] make 编译完成
- [x] make install 完成

### Phase 2.5: Conan 配方生成与验证
- [x] 基于 2.0.18 配方移植（版本号/URL/sha256/补丁集）
- [x] conan create test_package 通过

### Phase 3: 测试验证
- [x] conan create test_package 通过
- [x] test_mosquitto 调用 mosquitto_lib_init/version/new/destroy API
- [x] 上游 broker 套件 180/181 实跑
- [x] 上游 lib 套件 70/70 实跑
- [x] 上游 client 套件 4/4 实跑

### Phase 4: 归档收尾
- [x] 补丁复核（0002 保留并验证可干净应用；0001 已弃——上游 2.0.22 已升 cmake_minimum_required 到 3.18）
- [x] manifest.yaml 更新
- [x] 归档关闭

## 三、升级差异分析（2.0.18 → 2.0.22）

上游 ChangeLog 摘要（2.0.19..2.0.22 均为 bugfix 线，无构建系统重构）：
- 2.0.19: Security 修复（subscribe/unsubscribe 不匹配、bridge remapped topic 崩溃）
- 2.0.20: QoS 1/2 "no subscribers" 错误返回修复
- 2.0.21: Security 修复（恶意 SUBSCRIBE 内存泄漏 #248、CVE-2023-28366 追加修复）
- 2.0.22: broker/bridge/client library 稳定性修复

构建系统变化：
- 上游将 cmake_minimum_required 从 3.1 升至 3.18 → 2.0.18 的 0001 补丁不再需要
- config.h 的 FreeBSD 段有小改（_XOPEN_SOURCE 删除），补丁目标区上下文不变 → 0002 补丁可直接沿用（已 patch --dry-run 验证）
- OpenSSL 1.1 API 兼容宏 OPENSSL_API_COMPAT=0x10100000L 由上游自行添加，无需适配

## 四、平台修复

### 修复 1: config.h（补丁，保留自 2.0.18 并按 2.0.22 重新生成）
- 问题: HarmonyOS 不实现 pthread_cancel/pthread_testcancel (与 Android Bionic 相同)
- 修复: 添加 __OHOS__ 守卫，不定义 HAVE_PTHREAD_CANCEL
- 补丁: patches/0002-config.h.patch
- 注: 2.0.22 config.h 的 FreeBSD 段删除 2 行导致上下文整体上移，2.0.18 的补丁
  hunk 行号不再匹配（conan 内置 patch 严格按行号），已针对 2.0.22 源码树重新生成

### 修复 2: conanfile 增加 CMakeDeps 生成器（配方级）
- 问题: 上游 2.0.22 把 broker 链接从 `${OPENSSL_LIBRARIES}`（模块模式变量）
  改为 `OpenSSL::SSL` imported target。原配方无 CMakeDeps，
  find_package(OpenSSL) 命中本机 harmonybrew 的 config
  (`OpenSSL_DIR=/storage/Users/currentUser/.harmonybrew/lib/cmake/OpenSSL`)，
  链接到不带 libcrypto 的宿主 libssl.so，链接期 38 个 undefined symbol
  (X509_*/EVP_*/ERR_*)
- 修复: generators = "CMakeDeps"，find_package(OpenSSL) 命中 Conan 钉版的
  openssl/3.5.6.1（cmake_file_name=OpenSSL，targets OpenSSL::SSL/::Crypto）
- 验证: broker/libmosquitto/mosquitto_passwd 全部链接成功

### 修复 3: conanfile 工具链注入 OPENSSL_INCLUDE_DIR（配方级）
- 问题: 上游 lib/、client/、apps/、src/、plugins/ 各子目录的
  include_directories() 消费模块模式变量 `${OPENSSL_INCLUDE_DIR}`，
  而 config 模式 find_package（CMakeDeps）不定义该变量 →
  plugins/message-timestamp 等不链接 OpenSSL::SSL 的目标编译期
  `fatal error: 'openssl/opensslconf.h' file not found`
- 修复: CMakeToolchain 层注入
  `tc.variables["OPENSSL_INCLUDE_DIR"] = openssl.cpp_info.aggregated_components().includedirs`
  （根 CMakeLists 仅在 WITH_TLS=OFF 时清空该变量，工具链值可存活到全部子目录）
- 验证: 全部目标（含 4 个 plugin、mosquitto_pub/sub/rr、dynamic-security）编译通过

### 修复 4: conanfile 工具链注入 CJSON_* 桥接变量（配方级）
- 问题: 上游以 CamelCase `CJSON_FOUND` 等 gating clients(mosquitto_sub -F) 与
  dynamic-security 插件；Conan CMakeDeps 生成的变量是全小写 `cjson_*`
  （其 cmake_file_name=cjson），CMake 的 FIND_PACKAGE(cJSON) 只记录调用大小写
  `cJSON_FOUND`（config 模式不定义）→ 两者都空 →
  "Optional dependency cJSON not found" → 插件与 cJSON 特性被静默裁掉
- 修复: CMakeToolchain 层注入 `CJSON_FOUND=True / CJSON_LIBRARIES=cjson::cjson /
  CJSON_INCLUDE_DIRS=<conan cjson includedirs>`（cache 变量可达全部子目录，
  与 OPENSSL_INCLUDE_DIR 同模式）
- 验证: dynamic-security 插件随构建产出，14-dynsec-* 上游测试可跑
- （曾试 0003 源码补丁在 FIND_PACKAGE 后桥接小写变量，实测 cjson_FOUND 不存在
  而桥不触发——CMake 实际记录的是 cJSON_FOUND 混合大小写，故下沉到配方层为最终方案）

### 修复 5: src/CMakeLists.txt broker 符号导出列表扩展到 HarmonyOS（补丁 0004）
- 问题: CMake 对 HarmonyOS 是未知平台（System is unknown to cmake）→ `UNIX` 变量未设置
  → 上游 `if (UNIX)` 分支的 `-Wl,-dynamic-list=src/linker.syms`（broker 导出插件所需
  mosquitto_* 符号）被跳过 → 11 个 09-plugin-* 与 15 个 14-dynsec-* 上游测试失败于
  "Error relocating c/auth_plugin_v4.so: mosquitto_client_username: symbol not found"
- 修复: `if (UNIX)` → `if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`
- 验证: broker link.txt 出现 dynamic-list，nm -D 可见 mosquitto_client_username 等符号
- 补丁: patches/0004-src-CMakeLists.txt-harmonyos-dynamic-list.patch

## 五、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| config.h | HarmonyOS pthread_cancel 缺失 | 添加 __OHOS__ 守卫 | ✅ 0002-config.h.patch |
| src/CMakeLists.txt | HarmonyOS 未知平台 UNIX 未设 → 插件符号未导出 | dynamic-list 条件扩展 | ✅ 0004-src-CMakeLists.txt-harmonyos-dynamic-list.patch |
| conanfile.py | 2.0.22 上游改用 OpenSSL::SSL target 链接 | 增加 CMakeDeps 生成器 | 配方级，非补丁 |
| conanfile.py | config 模式无 OPENSSL_INCLUDE_DIR | 工具链注入 include 路径 | 配方级，非补丁 |
| conanfile.py | CMakeDeps 小写 cjson 变量与上游 CJSON_* gating 断链 | 工具链注入 CJSON_* 桥接变量 | 配方级，非补丁 |

## 六、验证记录
- conan create -pr=ohos-aarch64 全绿（含 test_package 消费者测试）
- test_mosquitto 实测输出: `mosquitto version: 2.0.22` / `All tests passed`
- 上游测试套件本机实跑（本机即 OHOS PC aarch64，交叉编译产物原生运行，非模拟）:
  - broker 套件（test/broker/test.py 注册 181 项）: **180/181 通过**
    - 修复链实证: 修复前 151 绿/30 红（15×dynsec 插件未构建+11×plugin 符号未导出+1×psutil+3×其他）
    - 0004 补丁生效后 plugin/dynsec 全部转绿（详见修复 5）
  - lib 套件（test/lib/test.py 注册 70 项 = C 47 + C++ 23）: **70/70 通过（100%）**
    - 初跑全红为测试环境相对路径解析（构建树无版本化 SONAME），非适配缺陷（见下）
  - client 套件（test/client/test.sh）: **4/4 通过**（subscribe/pub-sub/file-publish/stdin）
  - unit 套件（6 个二进制）: 上游依赖 CUnit（`fatal error: 'CUnit/CUnit.h' file not found`），
    OHOS 无 CUnit 二进制包，环境限制不可执行（未计入实跑）

## 七、上游测试环境布局说明（非适配缺陷定性）
上游 makefile 测试套件按"源码树 make 构建产物"的路径布局设计，Conan CMake 构建产物在
`build/Release/` 下，直接跑需要软链对齐（本次实跑用的全部对齐操作，均不在交付物内）:
- `src/mosquitto`、`client/mosquitto_{pub,sub,rr}`、`apps/*/mosquitto_{passwd,ctrl}`、
  `lib/libmosquitto.so.1`、`lib/cpp/libmosquittopp.so.1`
- `plugins/dynamic-security/mosquitto_dynamic_security.so`（14-dynsec-* 测试的相对路径）
- conan 构建的 so 无版本化 SONAME（NO_VERSIONED_SONAME 是 conan 共享库包标准行为），
  测试二进制 NEEDED 记录相对路径 `../../../lib/libmosquitto.so.1`，按上游布局建软链后全部通过
- test/lib/c 测试二进制编译需注入 conan openssl include/lib 路径（上游 config.mk 假定宿主 openssl）

## 结束记录
- **最终状态**: built (本地 conan create 全绿 + 上游 broker 180/181 + lib 70/70 + client 4/4)
- **结束时间**: 2026-10-08

## 结束记录
- **最终状态**: built (本地 conan create 全绿)
- **结束时间**: 2026-10-08
