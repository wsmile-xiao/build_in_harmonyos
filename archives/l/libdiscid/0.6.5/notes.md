# libdiscid 0.6.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 状态: built
- 平台: HarmonyOS PC (aarch64)
- 源码来源: https://github.com/metabrainz/libdiscid/releases/download/v0.6.5/libdiscid-0.6.5.tar.gz

## 软件信息
- 名称: libdiscid
- 版本: 0.6.5
- 上游仓库: metabrainz/libdiscid
- 许可证: LGPL-2.1-or-later
- 描述: MusicBrainz DiscID library for audio CD identification
- 产物: libdiscid.a (静态库) + discid/discid.h (头文件)
- 依赖: 无外部依赖

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - OHOS 平台删除 shared 选项（HarmonyOS 仅支持静态库）
  - exports_sources = "patches/*"
- `conandata.yml`: 源码 URL + 已验证的 SHA-256
- `test_package/`: 测试包，编译链接测试程序验证库核心功能

## 编译步骤

1. Conan 下载源码：`get(self, **self.conan_data["sources"], strip_root=True)`
2. 生成工具链：`CMakeToolchain`
3. 配置：`cmake.configure()`
4. 构建：`cmake.build()`
5. 安装：`cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 强制构建共享库 | `ADD_LIBRARY` 硬编码 `SHARED` | 补丁移除硬编码类型，并在 OHOS 上显式设置 `BUILD_SHARED_LIBS=OFF` |
| 2 | 源码完整性校验 | 下载归档需要固定校验值 | 使用实测 SHA-256 `72dbb493e07336418fe2056f0ebc7ce544eedb500bb896cc1cc04bd078c2d530` |

## 验证结果

test_package 验证 libdiscid 核心功能，编译链接测试程序验证库核心功能。

## 注意事项

- libdiscid 为依赖项范畴
- 默认静态构建（shared=False），符合系统库规则
