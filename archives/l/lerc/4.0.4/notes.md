# lerc 4.0.4 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libLerc.so，供 dlopen 及作依赖。
- libtiff 的 LERC codec 依赖。

## 关键适配
- 构建系统：cmake（CMakeLists.txt 根目录）
- 4.0.4 (js_v4.0.4 分支) 已自带 `#include <algorithm>`（fpl_EsriHuffman.cpp / fpl_Lerc2Ext.cpp），无需补丁
- 需要补丁：add-missing-climits（fpl_Compression.cpp 使用 UINT_MAX 但缺少 `#include <climits>`）
  - 来源：https://github.com/Esri/lerc/commit/1fc73694263f53cf029c8cac2e632170880f56d4
- OHOS 适配：使用 _ohos_toolchain() 自发现 ohos.toolchain.cmake，裸 cmake 绕开 conan_toolchain（ML-0035）
- 产物 libLerc.so DT_NEEDED libc++_shared.so（C++ 库特性），真机需确认加载器可解析
- _sign_shared_libs() 重签名：剥离旧 .codesign + binary-sign-tool -selfSign
- package_info：cpp_info.libs=['Lerc']，cmake_file_name='LERC'，cmake_target_name='LERC::LERC'
- Linux/OHOS 平台添加 system_libs=['m']
- settings.os 判断使用 in ("Linux", "OHOS")（R32 铁律）

## 探索阶段编译记录
- cmake 配置参数：-DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=ON
- 编译器：clang 15.0.4 (OHOS SDK 26.0.0.18)
- 产物：libLerc.so.4 (SONAME=libLerc.so.4)，libLerc.so (symlink)
- DT_NEEDED: libc++_shared.so, libc.so

## 状态
published — conan create + conan-verify 已通过
---

**编译结束**: 2026-07-27 11:44
**最终状态**: published
