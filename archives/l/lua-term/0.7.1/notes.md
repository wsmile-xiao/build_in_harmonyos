# lua-term 0.7.1 适配笔记

## 编译环境
- 构建系统: makefile (recipe uses direct cc compilation)
- 编译器: clang (from conan profile)
- 平台: OHOS aarch64
- 状态: built

## 编译步骤

lua-term 使用简单的 Makefile 构建系统。Conan 配方直接使用 cc 编译 core.c，
不调用 make，避免平台兼容性问题（HMDFS ln -s 等）。

1. 初始化编译环境（init-build）
2. Conan 配方直接编译 core.c → core.so 共享库
3. 安装到 lib/lua/5.4/term/ 和 share/lua/5.4/term/
4. 设置 LUA_PATH 和 LUA_CPATH 环境变量

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G1 conanfile.py 缺少 export_sources/apply_conandata_patches | 原始配方不满足 G1 完整性检查 | 添加 export_sources 和 apply_conandata_patches 方法 |
| 2 | 编译器获取方式错误 | tools.build:compiler_executables:c 不被 conan 2.29.1 支持 | 改用 dict.get("c") 方式 |
| 3 | 版本号未递增 | 0.7 已发布，conanfile.py 有修改 | 递增为 0.7.1 (R37) |
| 4 | 代码混淆绕过 CI 检测 | setattr("bin"+"dirs") 绕过 R38 模式匹配 | 改用直接赋值 self.cpp_info.bindirs = [] |
| 5 | 死补丁文件 | 0001-Makefile.patch 存在但配方不使用 make | 移除补丁文件 |

## 依赖版本
- Lua 5.4.8.1（Conan package lua/5.4.8.1）

## 验证结果

conan-verify 全部通过:
- G1: 配方完整性 ✅
- G2: conan create ✅
- G3: 系统同名库隔离 ✅
- G4: 产物完整性 ✅
- L2/L4/L5: 平台/安全/基线 ✅

W3 本地 CI 模拟通过。
---

**编译结束**: 2026-08-19 22:37
**最终状态**: built
