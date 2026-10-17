# 适配笔记 — extra-cmake-modules 6.19.0

## 2026-07-18 适配（2026-07-23 本地验证通过）

### 环境
- 开发机：鸿蒙 PC（HMDFS 沙盒，/tmp 只读）
- 构建工具：/data/service/hnp/bin/{cmake,make,ninja,clang,clang++}
- 缺失：python3/pip3/conan/curl/wget/sh/sed/head/tail/mkdir（busybox 提供基础命令）

### 编译流程（实测通过）
```bash
busybox wget -O ecm.tar.xz "http://ftp.ntu.edu.tw/pub/kde/stable/frameworks/6.19/extra-cmake-modules-6.19.0.tar.xz"
busybox tar -xf ecm.tar.xz -C extracted/
cd extracted/extra-cmake-modules-6.19.0
busybox mkdir -p build-ohos && cd build-ohos
cmake -DCMAKE_INSTALL_PREFIX=$STAGING/usr ..
make -j1
make install DESTDIR=$STAGING
ctest --timeout 5 -j1  # 部分测试因缺 Python3/Sphinx 失败，非适配缺陷
```

### 关键发现

1. **DESTDIR 双重路径**：cmake DESTDIR 与 CMAKE_INSTALL_PREFIX 拼接为
   `$DESTDIR/$PREFIX/share/ECM/`，这是 cmake 标准 behavior，非 bug。
   Conan recipe 的 package() 应直接从源码树 copy 到 share/ECM/，绕过 DESTDIR 拼接。

2. **HarmonyOS 平台识别**：cmake 报 "System is unknown to cmake, create: Platform/HarmonyOS"
   非阻塞，cmake 自动 fallback 用 Linux config。但建议 CI 预置 HarmonyOS.cmake Platform 文件。

### 测试失败模式
   - ExecuteKDEModules / KDEFetchTranslations / KDEInstallDirsTest — 需 Python3
   - ecm_add_tests — 需 Python3
   - ECMCheckOutboundLicense — 需 ReuseTool
   非适配缺陷（conan create 本地验证通过，test_package 输出 `ECM find_package + ecm_install_dirs: OK`）。

### Conan recipe 特殊处理

- ECM 是 cmake-only 模块包，无 cpp_info.libs（不声明库）
- 下游通过 find_package(ECM) 引用，cpp_info.builddirs 告知 ECM 模块路径
- package() 直接从源码树 copy 到 share/ECM/{modules,kde-modules,find-modules,toolchain,cmake}/

### 版本号策略（R37）
- 首次适配上游 6.19.0 → 版本号 6.19.0
- 若后续修复适配问题 → 6.19.0.1, 6.19.0.2...

### 下游链
kdoctools 6.19.0 → ki18n 6.19.0 + karchive 6.19.0 + ECM 6.19.0 + Qt6 + libxml2 + libxslt
本次 ECM 适配是 kdoctools 链的第一环（最底层依赖）。
