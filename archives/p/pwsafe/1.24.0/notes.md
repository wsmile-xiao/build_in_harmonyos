# pwsafe 1.24.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 cmake + make 编译（CLI-only 模式）：
```bash
cmake -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=HarmonyOS \
  -DNO_WX=ON -DNO_GTEST=ON -DNO_YUBI=ON \
  -DHARDEN_USE_SAFE_STACK=OFF \
  -DCMAKE_INSTALL_PREFIX=$PREFIX .
make -j4
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | 缺少平台条件 | 添加 HarmonyOS 到平台匹配正则 |
| 2 | secure_getenv 不可用 | OHOS musl 缺少此函数 | 用 getenv 替代，#ifdef __OHOS__ |
| 3 | keystub.cpp syscall 缺失 | seteuid 等在 OHOS 上未实现 | 添加 __OHOS__ 条件跳过 |
| 4 | run.cpp 编译错误 | /proc 文件系统差异 | 添加 __OHOS__ 守卫适配 |
| 5 | StringX.cpp mbstate_t 问题 | 头文件包含差异 | 显式包含 wchar.h |
| 6 | version.in 模板路径问题 | 本地路径硬编码 | 替换为可移植路径 |
| 7 | PFileXMLProcessor.cpp wxWidgets include 未守卫 | 与 PFilterXMLProcessor.cpp 相同问题 | 添加 NO_WX 守卫 |
| 8 | clang-15 SafeStack ICE | AArch64 指令选择崩溃 | HARDEN_USE_SAFE_STACK=OFF |
| 9 | libmagic 无 conan 配方 | file 包无 conan recipe | make find_package optional |

## Conan 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.6.1 | 加密库 |
| uuid | 2.40.1 | UUID 生成 |
| curl | 8.15.0 | URL 传输 |
| libmagic | (optional) | 文件类型检测，无 conan 配方时自动跳过 |

## 构建产物

- pwsafe-cli: 密码管理 CLI 工具
---

**编译结束**: 2026-08-18 21:45
**最终状态**: built
