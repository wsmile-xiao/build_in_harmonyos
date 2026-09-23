# keditbookmarks

KDE 书签编辑器（KDE Gear 26.04.0，Qt6/KF6）。

## 描述

上游形态为 keditbookmarks GUI 编辑器（书签组织/编辑/导入导出，支持
XBEL、Netscape、IE Favorites、Opera、Galeon、KDE2 等格式）+
kbookmarkmerger 命令行合并工具，以及私有共享库 libkbookmarkmodel。
在 HarmonyOS PC 上交付全部两个可执行文件与私有库；KF6::Parts HTML
part 回退路径与 Qt6 DBus 单实例检测因平台无对应运行时被裁剪。

## 已编译版本

- 26.04.0 (2026-09-19)

## 特性

- XBEL 书签树编辑（增删改/分组/排序/搜索）
- 多格式导入导出（Netscape/Mozilla/IE/Opera/Galeon/KDE2/HTML）
- KIO 图标获取管线（KIO::favIconForUrl + KIO::FavIconRequestJob）
- kbookmarkmerger 外部书签合并

## 使用方法

```sh
# GUI 编辑器（需要图形环境）
keditbookmarks [bookmarks.xml]

# 无头导入导出
keditbookmarks --importkde3 in.xml --exportns out.html

# 合并外部书签文件
kbookmarkmerger <external-bookmarks-file>
```

```cmake
# 私有库无 CMake 导出目标；直接链接
find_library(KBOOKMARKMODEL_LIB kbookmarkmodel PATH_SUFFIXES lib)
```
