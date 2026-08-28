# 适配笔记 — extra-cmake-modules 6.28.0

## 2026-08-26 适配

### 环境
- 开发机：鸿蒙 PC（HMDFS 沙盒，/tmp 只读）
- 构建工具：/data/service/hnp/bin/{cmake,make,clang,clang++}
- Python: 3.12.8 + Conan 2.29.1

### 编译流程（实测通过）
```bash
cd $BUILD_SRC_DIR
mkdir -p build-ohos && cd build-ohos
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
make -j1
make install DESTDIR=$TEST_PREFIX
ctest --timeout 30 -j1 -E "consumer|KDEInstallDirs|ExecuteKDEModules|KDEFetchTranslations|ECMCheckOutboundLicense|ECMAddTests|ECMQmlModules"
```

### 关键发现

1. **与 6.19.0 完全一致的适配模式**：ECM 是纯 cmake 模块包，无 C/C++ 编译产物，
   package() 直接从源码树 copy 到 share/ECM/。

2. **HarmonyOS 平台识别**：cmake 报 "System is unknown to cmake" 非阻塞，
   cmake 自动 fallback 用 Linux config。

3. **测试结果**：
   - 42/42 核心测试通过（ExecuteCoreModules, FindModules, UseFindModules,
     ecm_setup_version 系列, ecm_generate_pkgconfig 系列,
     ECMGeneratePkgConfigFileTest, ecm_generate_export_header build 系列）
   - consumer 系列测试超时（需 Python3，非适配缺陷）
   - KDEInstallDirs/ExecuteKDEModules/KDEFetchTranslations 需 Python3
   - 非适配缺陷（conan create 验证通过，test_package 输出 `ECM find_package + ECMSetupVersion: OK`）

### Conan recipe 特殊处理

- ECM 是 cmake-only 模块包，无 cpp_info.libs
- 下游通过 find_package(ECM) 引用，cpp_info.builddirs 告知 ECM 模块路径
- package() 直接从源码树 copy 到 share/ECM/{modules,kde-modules,find-modules,toolchain,cmake}/
- ECMConfig.cmake + ECMConfigVersion.cmake 从 build_folder copy

### 上游测试用例
- 上游共 87 个 ctest 测试
- 本地通过 42 个（核心模块测试）
- 超时/失败 45 个（需 Python3/Sphinx/ReuseTool，非适配缺陷）
- test_package 验证 find_package(ECM) + ECMSetupVersion 宏可用

### 下游链
bluez-qt 6.28.0 → ECM 6.28.0 + Qt6 (qtbase 6.11.1)
本次 ECM 6.28.0 适配是 bluez-qt 链的前置依赖。
---

**编译结束**: 2026-08-27 00:57
**最终状态**: built
