# libzim 9.7.0.1 编译笔记

## 基本信息

- 软件名称：libzim
- 版本：9.7.0.1
- 构建系统：meson
- 编译日期：2026-08-11

## 版本说明

9.7.0.1 是 9.7.0 的适配修复版本（R37）。修复了 ELF 签名失效问题。

## 修复内容

### 签名问题修复

**根因**：`build()` 和 `package()` 方法中使用临时文件 + `shutil.move()` 方式签名，
在 HMDFS 文件系统上 `shutil.move()` 替换文件后 .codesign 签名数据与 ELF 文件内容
不一致，导致签名失效。OHOS 动态链接器拒绝 dlopen，返回 "Permission denied"。

**修复**：改为原地签名（in-place signing），即 `-inFile` 和 `-outFile` 使用同一路径，
通过 Conan 的 `self.run()` 执行。与 zstd/1.5.7 的签名方式一致。

**影响方法**：
- `build()` — 签名 libzim.so.9.7.0
- `package()` — 签名所有 libzim.so* 文件（含 symlink copyfile 副本）

## 编译过程

### 源码

源码来自官方 GitHub 仓库。

### 配置

使用 meson 构建系统，配置选项：
- --prefix=$DEFAULT_PREFIX

### 编译

使用 ninja 进行编译。

### 安装

安装到 ~/usr/local/

## 产物

- 库文件：libzim.so.9.7.0 (7.8M)
- 头文件：zim/*.h

## 状态

编译成功，已安装到本地。
---

**编译结束**: 2026-08-11 14:57
**最终状态**: built
