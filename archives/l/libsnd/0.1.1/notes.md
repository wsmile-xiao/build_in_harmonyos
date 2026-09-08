# libsnd 0.1.1 适配笔记

## 编译环境
- 构建系统: CMake (cmake_minimum_required 3.2.2，上游；配方打补丁升至 3.5)
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, /data/service/hnp/bin)
- 状态: published（conan create G2 通过，test_package 双测试全过）

## 编译步骤

```bash
# 1. 源码核验：官方 tag v0.1.1
#    https://github.com/everdrone/libsnd/archive/refs/tags/v0.1.1.tar.gz
#    SHA-256 236d4aad8f7cd67753dbd7a9afc41d2046ddc97b97ef9d2444bcf57eb0a12b64
# 2. 配方生成后修正为 CMake 模板（conan-init 误判 autotools，上游实为 CMake）
# 3. conan create 干净构建（G2 通过）
# 4. 上游测试独立构建运行：96/96 PASS（gtest）
# 5. test_package 双测试：test_libsnd（消费者）+ test_ohos（鸿蒙专项）均 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create configure 失败 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(3.2.2)`；CMake 4.1.2 移除 <3.5 兼容。tc.variables 写入 toolchain 文件晚于 cmake_minimum_required 执行，不生效 | patches/0001-cmake-min-version.patch 提升至 `cmake_minimum_required(VERSION 3.5)`（E103 既有知识；E187/DRAFT-E321 提供 cache_variables 备选） |
| 2 | test_package 消费者 CMakeDeps 报 `Library 'libsnd' not found in package` | 上游 `set_target_properties(libsnd PREFIX "")`，打包产物为 `libsnd.a`（无额外 lib 前缀）；`cpp_info.libs=["libsnd"]` 使 CMakeDeps 按 `liblibsnd.a` 查找落空 | `cpp_info.libs=["snd"]`（CMakeDeps 自动补 lib 前缀解析到 libsnd.a）——本轮新增知识，草稿 DRAFT-libsnd-0.1.1-prefix-empty-cppinfo-libs |
| 3 | test_package 构建 `Cannot determine link language for target` | 模板生成 test.c 但库是 C++（project CXX），CMake 无法判定链接语言 | 测试源改名为 test.cpp（C++ 消费者真实调用 snd API） |
| 4 | 上游测试独立构建需 googletest | 上游 CMake 通过 ExternalProject 从 git master 拉 gtest（网络/离线不稳） | 使用 Conan 缓存中已构建的 gtest（aarch64 ELF 匹配本机），手工链接运行 |

## 源码修改

- `patches/0001-cmake-min-version.patch`：`cmake_minimum_required( VERSION 3.2.2 )` → `cmake_minimum_required( VERSION 3.5 )`

## 依赖版本

- 无第三方运行时依赖（纯 C++14 静态 DSP 库）
- 测试依赖: googletest（Conan 缓存已有 aarch64 构建）

## 验证结果

```bash
# 上游测试（gtest，独立构建于 $HOME/tmp/builds/libsnd-0.1.1.work/build-upstream-test/）
./upstream_test            # [==========] 96 tests from 8 test suites ran. [PASSED] 96 tests.
                           # 日志 SHA-256 8ca47ed6f6943161b5a171f35f7ec1d22e2244bc4ebbf4f77647a6cc6810ca10
# 鸿蒙专项测试（$HOME/tmp/builds/libsnd-0.1.1.work/）
./ohos_specific_test       # 8/8 PASS（aarch64 探针 sysname=HarmonyOS、denormal、interp、FlipFlop）
                           # 日志 SHA-256 d49dd4ea4cfdd01274b1f82caaa4cd799ae4ea39b824e3ac785a9582385fec47
# conan create（G2）test_package
ctest                      # 1/1 test_libsnd Passed + 1/1 test_ohos Passed（100%）
```

## 测试统计（双口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 96 | 官方 tag 源码 9 个测试文件活跃 TEST() 声明（approx 21 / conversion 24 / denormal 5 / interpolation 33 / lfo 6 / saturator 4 / sine 1 / utils 2；bilinear.cpp 仅 1 个注释掉的 TEST，非独立用例） |
| configured_executable_total | 96 | gtest 注册 96 项（`--gtest_list_tests` 实测 96 项，8 个 suite） |
| executed_passed_total | 96 | 全量运行 PASSED（96/96 = 100.0%），0 失败 |
| 未运行/未实例化 | 0 | 上游 `add_test()` 在 CMakeLists 中被注释（无 ctest 注册），gtest 注册即全量运行 |
| test_package | 2/2 | test_libsnd + test_ohos 均 PASS（ctest） |

映射：源码 TEST() 声明 → 无条件编译（BUILD_TESTS=ON 无互斥分支）→ test 可执行目标 →
gtest 注册 96 项 → 实际运行日志 `[PASSED] 96 tests`。

## 知识候选台账与查重（任务第 6 步）

### 候选 1：CMake 4.x 拒绝 cmake_minimum_required < 3.5
- 真实错误：`Compatibility with CMake < 3.5 has been removed`（G2 configure）
- 根因：CMake 4.1.2 移除 <3.5 兼容策略；tc.variables 写入 toolchain 文件在项目
  cmake_minimum_required 之后才被读取，故不生效
- 修复：patches 补丁提升至 3.5（配方的 CMAKE_POLICY_VERSION_MINIMUM 变量保留作
  双保险但实际由补丁生效）
- 验证：conan create G2 通过（真实日志 + exit 0）
- 适用范围：所有声明 cmake_minimum_required < 3.5 的老 CMake 工程
- 四范围查重：**正式命中**（graph/E103.kv、doc/E103.md、index.tsv 行 329）+ 草稿
  DRAFT-E321-cmake4-policy-version-minimum.kv（cache_variables 备选）+ E187
- 七轴：exact_duplicate=否（E103 建议 bump-min-version，本任务正是此修法，属于
  **solution_overlap=完全覆盖**，复用既有知识）；trigger_overlap=是；causal=是
- 决定：**复用既有知识（E103/E187/DRAFT-E321），不新建条目**

### 候选 2：上游 CMake 目标 PREFIX "" → CMakeDeps 找不到库，cpp_info.libs 需去 lib 前缀
- 真实错误：`Library 'libsnd' not found in package. If 'libsnd' is a system library,
  declare it with 'cpp_info.system_libs' property`（test_package CMakeDeps 配置期）
- 根因：上游 `set_target_properties(libsnd PREFIX "")` → 打包产物 `libsnd.a`（无
  额外 lib 前缀）；`cpp_info.libs=["libsnd"]` 让 CMakeDeps 按 `lib<name>.a` 拼
  `liblibsnd.a` 落空。包内库真实存在，不是系统库，按报错提示加 system_libs 是错误方向
- 修复：`cpp_info.libs=["snd"]`（CMakeDeps 自动补 lib 前缀解析到 libsnd.a）
- 验证：conan create G2 消费者全链路通过（configure/compile/link/run，双测试 PASS）
- 适用范围：所有上游 CMake 对库目标设 PREFIX "" / CMAKE_STATIC_LIBRARY_PREFIX 为空的包
- 四范围查重：**未命中正式条目**。engine 命中 E221（Phase B: 2）但为触发层重叠
  （同为 "not found in package"/CMakeDeps 元数据类），根因（PREFIX "" 命名）与
  rec_approach（CLI+库建模）不同；graph/doc/index 无 PREFIX 命名条目
- 七轴：
  - exact_duplicate: 否
  - causal_duplicate: 否（E221 根因是 package_type 建模错误，本候选是归档命名）
  - trigger_overlap: 是（CMakeDeps "not found in package" 同触发器）
  - solution_overlap: 部分（都指向核对 cpp_info 与安装物一致，但修复动作不同）
  - combination_novelty: 是（PREFIX "" → libs 去前缀的对应关系为新增组合）
  - boundary_novelty: 是（适用边界：仅 CMake PREFIX 属性静态库，非动态/其他构建系统）
  - test_migration_novelty: 否（无测试迁移维度差异）
- 决定：**new_draft（路径 B）**，草稿对
  knowledge/drafts/DRAFT-libsnd-0.1.1-prefix-empty-cppinfo-libs.{kv,md}
  关系字段：similar_to=E221（触发层重叠）、其余空

### 候选 3：test_package project(CXX) 但源文件 .c → 链接语言判定失败
- 真实错误：`CMake Error: Cannot determine link language for target "test_libsnd"`
- 根因：模板生成 test.c，C++ 库的 test_package 声明 project(... CXX) 后 CMake
  无法为 .c 源判定链接语言
- 修复：测试源改名为 test.cpp
- 验证：conan create G2 通过
- 适用范围：C++ 库 test_package 源文件扩展名与 project 语言声明一致
- 四范围查重：engine 命中 E278（Phase B: 0，仅关键词），根因（条件 add_subdirectory
  目标缺失）与本候选不同，无实质覆盖
- 七轴：exact_duplicate=否；causal=否；trigger_overlap=弱；solution_overlap=弱；
  其余=否。属模板/拼写类小坑，独立知识价值低
- 决定：**不建条目**，已在 notes.md 记录（path A 内部处理）

### 路径决定
- 候选 1 复用既有知识（E103/E187/DRAFT-E321）
- 候选 2 已验证、可跨库复用（任何 PREFIX "" 的 CMake 静态库）、查重未命中/部分覆盖
  → **路径 B（new_draft）成立**，PR 前缀【知识库扩展】
- 候选 3 低价值不建条目
- 结论：`new_draft`（DRAFT-libsnd-0.1.1-prefix-empty-cppinfo-libs 随本 PR 入仓）

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libsnd/0.1.1/conanfile.py | CMake 配方（static、BUILD_TESTS=OFF、libs=["snd"]） |
| archives/l/libsnd/0.1.1/conandata.yml | 官方 URL + SHA-256 + 补丁声明 |
| archives/l/libsnd/0.1.1/patches/0001-cmake-min-version.patch | cmake_minimum_required 3.5 |
| archives/l/libsnd/0.1.1/test_package/ | conanfile.py + CMakeLists.txt + test.cpp + ohos_specific_test.cpp + MANIFEST.yml |
| knowledge/drafts/DRAFT-libsnd-0.1.1-prefix-empty-cppinfo-libs.{kv,md} | 路径 B 草稿 |

## 注意事项

- 上游 CMakeLists 中 `add_test()` 被注释（无 ctest 注册），测试入口为 gtest 可执行
  文件 test（main.cpp RUN_ALL_TESTS）；上游 project VERSION 声明 0.1.0 与 tag
  v0.1.1 不一致，属上游疏漏，不影响产物
- 禁止把 CMakeDeps "not found in package" 误判为系统库缺失而加 system_libs
---

**编译结束**: 2026-09-06 02:02
**最终状态**: published
