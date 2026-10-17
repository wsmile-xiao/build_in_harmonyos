# dcmtk 3.6.7 适配笔记

## 编译环境
- 构建系统: CMake
- 编译器: clang 15 / clang++ 15
- 目标平台: HarmonyOS aarch64 (OHOS)
- 状态: built

## 适配策略

### OHOS 平台守卫 (E092)
- 设置 CMAKE_SYSTEM_NAME=Linux
- 设置 CMAKE_SYSTEM_PROCESSOR=aarch64
- 仅在 self.settings.os == "OHOS" 时生效

### 交叉编译 (DCMTK_NO_TRY_RUN)
- 使用官方 DCMTK_NO_TRY_RUN 机制跳过 try_run 探测
- 预设 STL 特性测试结果 (C++11 保证可用)
- libiconv: 预设 DCMTK_ICONV_FLAGS_ANALYZED 和 FIXED_ICONV_CONVERSION_FLAGS

### 版本限制 (3.6.7 < 3.6.8)
- oficonv 模块不可用，charset_conversion 必须为 "libiconv"
- 无 dcmxml 模块
- 组件结构: ofstd 携带 system_libs (非 oficonv)

### 依赖
- 全部 6 个可选依赖已适配: zlib, openssl, libpng, libtiff, libxml2, libiconv
- icu 未适配，默认禁用 (DCMTK_WITH_ICU=OFF)

### 补丁 (4 个 CCI 补丁)
1. 0001-cmake-robust-deps-handling: find_package REQUIRED + imported targets
2. 0002-cmake-check-openssl-symbol: check_symbol_exists 替代 CHECK_FUNCTIONWITHHEADER
3. 0003-ambiguous-overload-operator-equal: C++20 operator== 歧义修复
4. 0004-fix-two-segmentation-faults: CVE-2024-34508/34509 修复

## 风险预判
1. CMake 平台检测: HarmonyOS 不在 CMake 已知平台列表 -> 设置 CMAKE_SYSTEM_NAME
2. try_run: 交叉编译无法运行目标二进制 -> DCMTK_NO_TRY_RUN
3. socket/pthread: dcmnet/dcmtls 需验证 OHOS musl 兼容性
4. iconv: oficonv 自带实现与系统 iconv 冲突 -> 3.6.7 无 oficonv，用 libiconv
5. ELF 签名: package() 后二进制需签名才能执行
