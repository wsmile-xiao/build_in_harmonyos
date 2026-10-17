# HiGHS 1.13.1 适配笔记

## 编译环境
- 系统：OHOS PC (arm64)
- 编译器：clang/clang++ (OHOS 工具链)
- CMake：OHOS 工具链内置
- Conan：2.29.1

## 编译步骤
```bash
conan create archives/h/highs/1.13.1/ --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMakeLists.txt 禁止在源码目录构建 | 第 35 行 `if(EXISTS "${LOC_PATH}")` 检查 conan 的构建目录下有 CMakeLists.txt | 创建补丁 `0001-disable-out-of-source-check.patch`，将 `if(EXISTS "${LOC_PATH}")` 改为 `if(FALSE)` |

## 源码修改

- `0001-disable-out-of-source-check.patch`: CMakeLists.txt 第 35 行跳过 out-of-source 构建检查

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| clang/clang++ | OHOS 工具链 | C++11 编译器 |
| CMake | >= 3.15 | 构建系统 |

## 验证结果
- conan create 编译通过
- test_package API 调用验证通过（创建 HiGHS 求解器实例并调用 run()）

test_package 验证：编译 test.c 调用 HiGHS API（`Highs::run()`），确认库可正常初始化。

## 注意事项
- HiGHS 是纯 C++ 线性优化库，无第三方依赖
- CMakeLists.txt 有 out-of-source 构建强制检查，已通过补丁绕过
- 仅适配路径 A（基础编译适配），无鸿蒙特有功能增强
