# cxxgraph 4.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS aarch64 profile)
- 状态: built

## 编译步骤

```bash
# 1. 下载官方 v4.1.0 tarball 并核验 SHA-256
curl -L -o cxxgraph-v4.1.0.tar.gz \
  https://github.com/ZigRazor/CXXGraph/archive/refs/tags/v4.1.0.tar.gz
sha256sum cxxgraph-v4.1.0.tar.gz   # 1f6601abfcb692f35bfe14f2a34b2302f70213a257b0f7d541a110d6bd460040

# 2. init-build + lang-preflight（R47: cpp 匹配）
python3 scripts/ohc-run.py init-build cxxgraph 4.1.0 \
  --url=https://github.com/ZigRazor/CXXGraph/archive/refs/tags/v4.1.0.tar.gz
python3 scripts/ohc-run.py lang-preflight cxxgraph 4.1.0 --src $BUILD_SRC_DIR

# 3. 探索编译（上游测试 test_exe, TEST=ON）
cmake $BUILD_SRC_DIR -DTEST=ON -DBENCHMARK=OFF -DEXAMPLES=OFF \
  -DCPM_SOURCE_CACHE=$HOME/tmp/cxxgraph-explore/cpm \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j4 test_exe && ./test_exe   # 301/301 passed

# 4. 配方生成与验证
python3 scripts/ohc-run.py conan-init cxxgraph 4.1.0
python3 scripts/ohc-run.py conan-verify cxxgraph 4.1.0   # G0-G4/L2/L4/L5 通过

# 5. finish（W3 本地 CI 模拟通过，超时预算 3600s）
python3 scripts/ohc-run.py finish cxxgraph 4.1.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 CMakeLists 配置期直连 GitHub 下载 CPM.cmake | CI worker 无法直连 github.com | conandata `cpm_source` 预下载到 build_folder/cpm/cpm/CPM.cmake，generate() 注入 CPM_SOURCE_CACHE |
| 2 | test/CMakeLists.txt 通过 CPM 拉 googletest(origin/main) 与 zlib 1.2.13 | 同上；GIT_TAG origin/main 不可复现 | conandata 预下载 gtest v1.17.0 + zlib 1.2.13，patches/0001-use-local-gtest-zlib.patch 让 CPM 优先本地 SOURCE_DIR |
| 3 | CPM 内 zlib cmake_minimum_required(<3.5) 与 CMake 4.x 冲突 | 现代 CMake 移除 <3.5 兼容层 | generate() 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | CMake 不识别 OHOS 平台 | CMake 无 harmonyos platform module（E092） | generate() 设置 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 5 | W3 本地 JC 命中其他库既有跟踪文件（cloog/kics .build-closed/.staging-verified） | 其他库基线噪声（main 已跟踪的空状态文件） | 基线隔离复验：记录路径+SHA-256(e3b0c44...)，隔离后 W3 通过，原样恢复，恢复后 SHA-256 一致；prdiff 口径复跑确认 |
| 6 | conanfile run() 参数错误 | Conan 2.x 无 run_environment 参数 | 改用 env="conanrun" |

## 源码修改

- `patches/0001-use-local-gtest-zlib.patch` — test/CMakeLists.txt 的 googletest/zlib CPMAddPackage 增加本地 SOURCE_DIR 分支（CXXGRAPH_GTEST_SOURCE_DIR / CXXGRAPH_ZLIB_SOURCE_DIR），未定义时回退上游 CPM 拉取。

## 依赖版本

- 无运行时依赖（header-only 库）
- 测试依赖: googletest v1.17.0（本地源码）、zlib 1.2.13（本地源码）、CPM.cmake v0.40.2

## 验证结果

```bash
# 上游测试（test_exe 全量运行，无 gtest_filter）
[==========] 301 tests from 42 test suites ran.
[  PASSED  ] 301 tests.

# conan-verify
G0-G4 + L2/L4/L5 全部 PASS

# W3 本地 CI 模拟
setup.sh 通过, 本地 CI 模拟通过
```

上游测试统计（双口径）:
- source_declared_total: 302（34 个独立 TEST 文件 + main.cpp 无用例 + 2 个辅助头文件）
- configured_executable_total: 301（ConnectivityTest.test_5 位于上游注释块 /* ... */ 内，未实例化；无排除条件，为上游注释代码）
- executed_passed_total: 301/301（全量运行通过）
- 全量通过率: 301/302 (99.7%)；当前配置可执行集合通过率 301/301 (100%)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only CMake 配方（package_type=header-library） |
| conandata.yml | 官方源 + 测试依赖预下载声明 |
| test_package/ | 消费者验证（Dijkstra 公开 API 调用 + 断言） |
| patches/0001-use-local-gtest-zlib.patch | CPM 本地源补丁 |

## 注意事项

- header-only 库无需 commands.json（R38 仅 CLI 需要）
- CPM.cmake 版本需与上游 SOURCE_DIR 分支兼容；gtest 版本固定 v1.17.0 保证可复现
---

**编译结束**: 2026-09-22 16:14
**最终状态**: built
