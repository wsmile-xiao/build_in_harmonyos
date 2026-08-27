# shared-mime-info

## 简介

shared-mime-info 是一个用于共享 MIME 类型信息的数据库和相关工具。它提供了一个中央数据库，用于存储文件类型和 MIME 类型的映射关系，被许多桌面环境和应用程序使用。

## 主要功能

- **update-mime-database**: 用于更新 MIME 类型数据库的工具
- **freedesktop.org.xml**: 标准的 MIME 类型定义文件
- **shared-mime-info.pc**: pkg-config 文件，用于其他软件查找依赖

## 版本信息

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.4 | built | 2026-08-22 | Conan 配方适配，完整构建（含 build-tools） |
| 2.5.1 | published | 2026-07-15 | Conan 配方，完整构建 |

## 依赖

- glib 2.84.0 (Conan)
- libxml2 2.15.3 (Conan)

## 编译说明

使用 Conan 构建，依赖通过 PkgConfigDeps + MesonToolchain 生成器管理。

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 补丁说明

无外部补丁。meson.build 的 test_tree_magic 变量修复在 build() 方法中动态注入。
