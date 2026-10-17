# HepMC3 3.1.2 OHOS 适配笔记

## 构建系统

- **类型**：CMake（上游最低要求 2.8.9，OHOS 上通过 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容）
- **编译器**：C++11（上游检测 `cxx_range_for` 等特性）
- **无外部依赖**：纯 C++ 标准库 + pthread（可选）

## OHOS 适配策略

### CMake 配置选项

| 选项 | 值 | 原因 |
|------|-----|------|
| `HEPMC3_ENABLE_ROOTIO` | OFF | OHOS 无 ROOT 框架 |
| `HEPMC3_ENABLE_TEST` | ON | 必须运行上游测试（R9/R12） |
| `HEPMC3_BUILD_EXAMPLES` | OFF | 减少编译时间 |
| `HEPMC3_INSTALL_INTERFACES` | OFF | Pythia8/Photos/Tauola 接口 OHOS 无需求 |
| `HEPMC3_ENABLE_SEARCH` | ON | search 库无外部依赖，可编译 |
| `CMAKE_POLICY_VERSION_MINIMUM` | 3.5 | 上游 cmake_minimum_required(2.8.9) 太老 |

### 库命名约定

- HepMC3 静态库命名为 `libHepMC3_static.a` 和 `libHepMC3search_static.a`
- `package_info()` 中根据 `shared` 选项声明不同库名
- shared=False 时 `package()` 删除 .so 文件，避免 OHOS RPATH 问题

### 上游 CMake 行为注意事项

- 上游 CMake **无条件构建 shared + static 两个版本**（忽略 `BUILD_SHARED_LIBS`）
- shared=False 时，`package()` 方法手动删除 .so 文件
- 上游 test/CMakeLists.txt 会构建 `MCEG3` 共享库（用于外部依赖测试），即使 MCEG 测试不运行也会编译该库——在 OHOS 上可能因 RPATH/linker 问题需要关注

## 上游测试分析

### 核心单元测试（HEPMC3_ENABLE_TEST=ON 时运行）

上游 test/CMakeLists.txt 定义 13 个核心测试：
```
testBoost, testMass, testPrintBug, testPolarization, testUnits,
testMultipleCopies, testWeights, testLoops, testDelete,
testIO1, testIO3, testIO6, testReaderFactory1
```
+ testThreads1（条件：Threads_FOUND）

### ROOT 依赖测试（HEPMC3_ENABLE_ROOTIO=OFF，豁免）

```
testIO2, testIO4, testReaderFactory2
```

### 外部依赖测试（find_package 守卫，豁免）

| 测试 | 所需包 | OHOS 状态 |
|------|--------|-----------|
| testPythia1, testPythia2 | Pythia8 | 不可用 |
| testPhotos1 | Photospp | 不可用 |
| testTauola1 | Tauolapp | 不可用 |
| testMCTester1 | MCTester + ROOT | 不可用 |

## 源码 URL 说明

- **官方源**：CERN GitLab `https://gitlab.cern.ch/hepmc/HepMC3/-/archive/3.1.2/HepMC3-3.1.2.tar.gz`
- **SHA256**：`4133074b3928252877982f3d4b4c6c750bb7a324eb6c7bb2afc6fa256da3ecc7`
- Debian 上游 tarball（`hepmc3_3.1.2.orig.tar.gz`）SHA256 一致，可作为镜像备选
- hepforge 源文件内容与 CERN GitLab 不同（独立打包），不可混用

## 平台兼容性

- C++17 标准（test_package 需要，上游只需 C++11）
- 无平台特定代码（纯标准 C++）
- 无补丁需求（CMake 项目，跨平台良好）
- pthread 链接（testThreads1 需要，OHOS 支持）

## 已知风险

1. **CERN GitLab 访问**：CI Worker 可能无法直连 gitlab.cern.ch，需关注镜像 fallback
2. **MCEG3 共享库**：test/CMakeLists.txt 无条件构建 MCEG3 SHARED 库，在 OHOS 上可能因 RPATH 设置失败
3. **testThreads1**：需要 pthread，OHOS 上 Threads_FOUND 通常为 true
