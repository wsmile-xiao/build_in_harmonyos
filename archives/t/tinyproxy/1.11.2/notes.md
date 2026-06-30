# tinyproxy 1.11.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. 修复 config.guess 和 config.sub 添加 ohos 平台支持
2. 由于 HMDFS 文件系统限制，无法在 `/storage/Users/currentUser` 目录创建临时文件
3. 将源码复制到本地文件系统 `/data/storage/el2/base/files/tinyproxy-build`
4. 在本地文件系统运行 configure: `../configure --prefix=/storage/Users/currentUser/usr/local`
5. 运行 make all 编译
6. 运行 make install DESTDIR=/storage/Users/currentUser/test-install-tinyproxy-1.11.2 安装到测试目录
7. 运行 make install 安装到本地 ~/usr/local 目录
8. 验证 tinyproxy --version 成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 在 HMDFS 上失败，config.status 无法创建临时文件 | HMDFS 文件系统限制，不支持某些类型的临时文件创建（mktemp/dfifo） | 将源码复制到本地文件系统 `/data/storage/el2/base/files` 进行编译 |
| 2 | config.guess/config.sub 不识别 ohos 平台 | E007/E072: GNU Config 缺少 ohos 支持 | 添加 ohos-linux 映射和 ohos* 白名单 |

## 源码修改

### 补丁列表

1. `0001-config.guess.patch` - 添加 ohos 平台识别
2. `0002-config.sub.patch` - 添加 ohos 三元组验证支持

### 主要修改

- config.guess: 在 Linux 检测分支中添加 HarmonyOS uname 识别，输出 `aarch64-unknown-linux-ohos`
- config.sub:
  - 在 maybe_os 行添加 `linux-ohos*` 和 `ohos*`
  - 在 OS 白名单添加 `ohos*`
  - 在 kernel-os 白名单添加 `linux-ohos*`

## 依赖版本

- clang 15.0.4
- make 4.4.1
- automake 1.16 (optional, not required for build)
- autoconf 2.71 (optional, not required for build)

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/tinyproxy --version
# 输出: tinyproxy 1.11.2

/storage/Users/currentUser/usr/local/bin/tinyproxy -v
# 输出详细信息，包括编译特性
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinyproxy | 317952 bytes | 主二进制文件 |
| 0001-config.guess.patch | 1099 bytes | 平台识别补丁 |
| 0002-config.sub.patch | 2570 bytes | 三元组验证补丁 |

## 注意事项

⚠️ **HMDFS 限制**: 由于 HMDFS 文件系统不支持创建某些类型的临时文件（如 config.status 需要的 fifo 和 mktemp），建议后续编译类似软件时：
1. 将源码复制到本地文件系统（如 `/data/storage/el2/base/files`）
2. 在本地文件系统完成 configure 和 make
3. 将构建产物复制回归档目录

⚠️ **G0 干净构建验证失败**: 由于 G0 验证尝试在 HMDFS 上解压并运行 configure，会因临时文件限制而失败。但实际构建已在本地文件系统验证通过。
---

**编译结束**: 2026-05-29 15:40
**最终状态**: built
