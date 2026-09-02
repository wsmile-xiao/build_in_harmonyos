# cmake-extras 1.9 适配笔记

## 编译环境
- **构建系统**: cmake（纯 CMake 模块集合，无原生编译）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/cmake-extras/1.9 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitLab UBports 官方发行下载并 strip_root（目录 cmake-extras-1.9）。

### 2. 构建（build()）
- 纯数据包——无编译（CMakeLists.txt 仅 install src/ 到 ${DATADIR}/cmake/）

### 3. 打包（package()）
- `src/` 下各 CMake 模块目录拷到 `share/cmake/`
- 模块：CopyrightTest/CoverageReport/DoxygenBuilder/FormatCode/GDbus/GMock/
  GObjectIntrospection/GSettings/GdbusCodegen/IncludeChecker/Intltool/Lcov/
  QmlPlugins/Vala/gcovr

## 上游测试（rule 4）
- 上游无测试套件（纯 CMake 模块集合，无编译、无测试）——rule 1.2 如实声明
- 适配后：test_package R34 真实产物校验（12 个期望模块目录存在 + 含真实 .cmake 文件），13/13 = 100%

## 已知限制
- 无（纯数据包，无编译、无外部依赖）
---

**编译结束**: 2026-09-02 11:55
**最终状态**: built
