# sophus 1.22.10 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify G1-G4/L2/L4/L5 通过，W3 本地 CI 100% pass）

## 编译步骤

```bash
# 1. init-build（源码经官方 release tag 1.22.10 tarball，核验 commit de0f8d3d92bf776271e16de56d1803940ebccab9）
python3 scripts/ohc-run.py init-build sophus 1.22.10 --url=https://github.com/strasdat/Sophus --tar tar.gz

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight sophus 1.22.10 --src $BUILD_SRC_DIR   # detected=cpp

# 3. 探索编译（调试用）
cmake -S . -B build -DEigen3_DIR=<eigen cmake> -DBUILD_SOPHUS_TESTS=ON -DBUILD_SOPHUS_EXAMPLES=OFF
make && ctest    # 13/13 通过

# 4. conan-init 生成配方 → 重写为 CMake header-only 配方（依赖 eigen/3.4.0）
# 5. conan-verify（G1-G4 全过）
python3 scripts/ohc-run.py conan-verify sophus 1.22.10
# 6. finish published（W2 结构 + R36 依赖 + W3 本地 CI）
python3 scripts/ohc-run.py finish sophus 1.22.10 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 报 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 3.4)` 低于 CMake 4.x 兼容下线 | patches/0001-CMakeLists.txt.patch bump 至 3.5（E103 等价命中）；`tc.variables` 注入 CMAKE_POLICY_VERSION_MINIMUM 在 toolchain 加载时序上不生效，弃用 |
| 2 | test_package 编译报 `fatal error: 'fmt/format.h' file not found` | 上游无 fmt target 时自动启用 basic logging，`SOPHUS_USE_BASIC_LOGGING=1` 仅写入上游导出目标，CMakeDeps 消费者只读配方 package_info，宏未传播 | package_info() 增加 `self.cpp_info.defines = ["SOPHUS_USE_BASIC_LOGGING=1"]`（DRAFT-sophus-1.22.10-fmt-basic-logging-macro） |
| 3 | test.cpp `Sophus::SO3d::log(R)` 报非静态成员函数 | 1.22.10 中 `log()` 是实例方法 | 改为 `R.log()` |

## 源码修改

- patches/0001-CMakeLists.txt.patch：`cmake_minimum_required(VERSION 3.4)` → `3.5`（仅此一处）

## 依赖版本

- eigen/3.4.0（ohpcd 已发布预编译包）

## 验证结果

```bash
# 上游测试 13/13（.work 调试构建）+
# conan create G2 通过（含 test_package 消费者实测 SO3/SE3 exp-log roundtrip）
# W3 本地 CI: L0 pass / L1e 破坏性负测通过 / Pass rate 100% (1/1)
```