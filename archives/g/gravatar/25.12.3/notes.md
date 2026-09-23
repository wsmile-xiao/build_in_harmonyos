# gravatar 25.12.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 通过 `init-archive` 初始化 `archives/g/gravatar/25.12.3`.
2. 通过 `conan-init` 生成 Conan recipe 骨架.
3. 将 recipe 收敛为 CMake shared library, tests disabled.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-init` 控制台编码报错 | Windows 控制台使用 GBK, 脚本输出 Unicode | 文件已生成, 继续手工收口 recipe |

## 源码修改

无

## 依赖版本

- qtbase/6.11.1
- kcoreaddons/6.18.0
- ki18n/6.18.0
- kconfig/6.18.0
- kconfigwidgets/6.18.0
- kwidgetsaddons/6.18.0

## 验证结果

```bash
待执行 `conan create`.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
无

## 注意事项

测试包使用 `KPim6Gravatar` 上游 CMake config, not a Conan-generated alias.
