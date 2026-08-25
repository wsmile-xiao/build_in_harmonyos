# ladybug 0.18.2 适配笔记

> 基于 0.19.1 适配经验打回重做（2026-08-21）：任务规定版本为 0.18.2，10 个补丁经校验可干净应用于 v0.18.2 源码。

## W3 本地 CI 门禁阻塞记录（环境性，非配方缺陷）

- **现象**：`finish` Step 3.5 (W3) 超时失败，`.ci-result.json` 未生成，状态保持 `built`。
- **根因**：`scripts/ohc/workflow_checks.py` `run_local_ci()` 对 `ci/conan/build_and_test.sh` 整段运行硬编码 `timeout=600`（10 分钟）；而 CI 脚本对目标包强制 `conan create --build=ladybug/*` 全量重建（实测约 25-35 分钟），且 ladybug 源码从 github.com 下载极慢（曾卡 40 分钟）。CI 真实预算为 `ci/config/build_timeouts.txt` 默认 3600s。
- **证据**：`.ci_logs/finish_ladybug.log` 显示 `build_and_test.sh 失败 (RC=1) / TIMEOUT`；`.ci_logs/conan_build_ladybug_0.19.1.log` 止于 `Calling source()`；libubox/at-spi2-core 因包小在 600s 内通过，证明这是大包 + 本地包装超时限制。
- **配方 CI 干净性**：conan-verify G0-G4 全通过（G2 conan create + test_package 实质测试 PASS：C API create/match roundtrip + `lbug --version` → `Lbug 0.18.2`）；10 个补丁无危险函数；L0 结构全过。
- **放行方案（需主编/CI 侧，协作者无权改 scripts/ 与 ci/）**：① `run_local_ci()` timeout 600→3600+ 或读取 build_timeouts.txt；② `ci/config/build_timeouts.txt` 加 `ladybug/0.18.2` 覆盖；③ conan-verify 已过的包 W3 本地重跑降级为 warn/skip，由真实 CI（3600s 预算）执行 L0-L5。
- **遵守 R9**：门禁未全通过，不得宣称 success、不得标 published。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-13
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin/clang++）
- CMake: 4.1.2
- Conan: 2.29.1（OHOS 适配版，os=OHOS/arch=armv8 profile: ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤

1. 下载源码 v0.18.2 tarball（sha256 `5423aae21009fe76d2f8dad2d2453f02a2045bdbd0293e8bedd81c80ef0b6376`），解压到
   `/storage/Users/currentUser/tmp/ladybug-0.18.2.work`（`.orig` 为原始副本）。
2. 生成并应用 10 个补丁（archives/l/ladybug/0.18.2/patches/0001-0010），覆盖 CMakeLists、C API、
   聚合函数、存储索引、simsimd 头文件等。
3. 走 Conan 配方构建（conan create 干净构建，等价于）：
   ```
   conan create archives/l/ladybug/0.18.2 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
     --build=missing --user=ohpcd --channel=stable
   ```
   - conanfile.py generate() 注入：
     `-DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64`
     `-DBUILD_SHARED_LBUG=OFF -DBUILD_STATIC_LBUG=ON -DBUILD_SHELL=ON`
     `-DBUILD_TESTS=OFF -DBUILD_EXTENSION_TESTS=OFF -DBUILD_SINGLE_FILE_HEADER=OFF -DENABLE_BACKTRACES=OFF`
   - 依赖 openssl/3.5.6.1.1（ohpcd 制品仓预编译包）。
4. `cmake --build` → `cmake --install`，产物：`bin/lbug`、`lib/liblbug.a`、`include/lbug.h`。
5. Staging 验证 + test_package（R34 C API 实质测试 + lbug --version smoke）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | simsimd 编译失败：`arm_sve.h: No such file or directory`、dotprod/fp16/bf16 内建函数未定义 | OHOS clang15 不支持 SVE 扩展，`target("arch=+dotprod/+fp16/+bf16")` 属性无法启用 NEON 扩展内建（vdotq_s32、bfloat16x8_t） | CMakeLists OHOS 分支禁用 `SIMSIMD_TARGET_SVE/SVE2/NEON_I8/NEON_F16/NEON_BF16`，仅保留 NEON baseline；simsimd 运行时 dispatch，向量查询仍走 NEON（patch 0001、0010） |
| 2 | `std::format` 链接错误：`__throw_format_error`、`std::format_error` undefined | OHOS 共享 libc++ (LLVM15) 的 `<format>` 符号收在 libc++experimental.a | `add_compile_definitions(_LIBCPP_ENABLE_EXPERIMENTAL)` + `add_link_options(-lc++experimental)`（patch 0001） |
| 3 | `std::atomic_ref` 不存在 | OHOS libc++15 未实现 C++20 std::atomic_ref | 改 `__atomic_exchange_n(&ptr, ...)` 内建（patch 0002/0003） |
| 4 | `dependent type` 缺 typename | clang15 严格模板解析 | 依赖类型前补 `typename`（patch 0004/0005/0006/0007/0008） |
| 5 | 结构化绑定捕获进 lambda 报错 | clang15 不允许 | 改为普通变量再捕获（patch 0009） |
| 6 | `-latomic` 链接失败 | OHOS 无 libatomic；aarch64 clang 内联 128 位原子（ldaxp/stlxp） | `CMAKE_SYSTEM_NAME=HarmonyOS` 时跳过 `list(PREPEND LBUG_LINK_LIBRARIES atomic)`（patch 0001） |
| 7 | 运行时 8TB mmap 失败（database init） | OHOS 用户态地址空间限制，默认 `max_db_size=8TB` 的 mmap 无法映射 | C API 测试/应用显式设置较小 `max_db_size`（test.c 用 256MB） |
| 8 | test_package 链接失败：`operator new`/`__cxa_begin_catch`/`std::mutex` 未定义 | test_ladybug 以 C 链接器链接（`LANGUAGES C`），而 liblbug.a 是 C++ 静态库，不自动带 libc++ 运行时 | `project(LANGUAGES C CXX)` + `set_target_properties(LINKER_LANGUAGE CXX)` 强制 C++ 链接器（test_package/CMakeLists.txt） |

## 发现与知识

- ✅ (ref:E100): OHOS clang15 无法编译 simsimd 的 SVE/dotprod/fp16/bf16 扩展 SIMD 后端，编译期禁用扩展仅保留 NEON baseline，simsimd 运行时 dispatch
- ✅ (ref:E247): C API 静态库含 C++ 实现时，test_package 必须 `LANGUAGES C CXX` + `LINKER_LANGUAGE CXX` 强制 C++ 链接器，否则 ld.lld 报 C++ runtime 未定义
- ✅ (ref:notes.md): OHOS 共享 libc++ (LLVM15) 的 std::format 符号位于 libc++experimental.a，需 `_LIBCPP_ENABLE_EXPERIMENTAL` + `-lc++experimental`
- ✅ (ref:notes.md): OHOS 无 libatomic，aarch64 clang 内联 128 位原子（ldaxp/stlxp），须跳过 CMake 默认 `-latomic`
- ✅ (ref:notes.md): OHOS libc++15 无 std::atomic_ref，改 `__atomic_exchange_n` 内建函数
- ✅ (ref:notes.md): clang15 严格模式要求依赖类型前补 `typename`、结构化绑定不可作为 lambda 捕获
- ✅ (ref:notes.md): OHOS 地址空间限制下默认 8TB mmap 失败，需显式设置较小 `max_db_size`（测试用 256MB）
- ✅ (ref:notes.md): openssl 预编译 binary 验证用 conan cache path / conan download（R35），禁止 conan list 判断
- ✅ (ref:notes.md): 消费者链接 liblbug.a 需传递 `-lc++experimental`（recipe `cpp_info.system_libs`，OHOS 分支）
- ✅ (ref:notes.md): W3 本地 CI 对 github 大包必然超时（600s 包装 vs 3600s 真实预算），需主编/CI 侧放行；门禁未过不得宣称 success（R9）

## 源码修改

10 个补丁见 `archives/l/ladybug/0.18.2/patches/`，全部为 OHOS 平台适配（portability），
不改变上游功能逻辑。

## 依赖版本

- openssl/3.5.6.1.1（静态库，OHOS aarch64 预编译，R35 已验证）

## 验证结果

```bash
# test_package C API 实质测试（R34）：创建内存库 → 建表 → 写节点 → 查询校验
./test_ladybug
# 输出: PASS: lbug C API (create/match roundtrip)

# lbug CLI smoke（L2）
./lbug --version
# 输出: Lbug v0.18.2 数据库版本信息（--version 支持）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/lbug | ~数 MB | 交互式 shell 命令行工具（R38 commands.json 已声明） |
| lib/liblbug.a | ~数十 MB | 静态图数据库库（C API，头文件 include/lbug.h） |

## 注意事项

- OHOS 下所有使用 liblbug 的程序必须设置合理的 `max_db_size`（默认 8TB mmap 会失败）。
- 依赖链传递：liblbug.a 引用 OpenSSL 符号，消费者需传递链接 `openssl::openssl`
  （conanfile.py `cpp_info.requires` 已处理）。
- CI 上 CMake 的 HarmonyOS 识别由 conanfile generate() 显式注入 `CMAKE_SYSTEM_NAME=HarmonyOS`
  保证，避免依赖 uname 推断。
---

**编译结束**: 2026-08-21 23:09
**最终状态**: built
