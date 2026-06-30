# libusbmuxd 2.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang
- 状态: published

## 编译步骤

1. 下载源码
   ```bash
   curl -k -L -o libusbmuxd-2.1.0.tar.bz2 \
     "https://github.com/libimobiledevice/libusbmuxd/releases/download/2.1.0/libusbmuxd-2.1.0.tar.bz2"
   tar -xjf libusbmuxd-2.1.0.tar.bz2
   ```

2. Configure
   ```bash
   export CC=clang
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig
   ./configure --prefix=~/usr/local
   ```

3. 修复 config.status 权限问题
   ```bash
   sed -i 's/umask 077 && mktemp -d/mktemp -d/g' config.status
   ./config.status
   ```

4. 编译安装
   ```bash
   make -j2
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报错 "umask 077 && mktemp -d" | HarmonyOS TMPDIR 权限限制 | 移除 config.status 中的 `umask 077` |
| 2 | configure 找不到 libplist 和 libimobiledevice-glue | 依赖未安装或 PKG_CONFIG_PATH 未设置 | 先编译依赖并设置 PKG_CONFIG_PATH |

## 源码修改

无补丁，仅修改生成的 config.status 文件（临时）

## 依赖版本

- libplist 2.3.0
- libimobiledevice-glue 1.3.0

## 验证结果

```bash
pkg-config --modversion libusbmuxd-2.0
# 输出: 2.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libusbmuxd-2.1.0-ohos-aarch64.tar.gz | 678 KB | 预编译包 |
| libusbmuxd-2.1.0-ohos-aarch64-debug.tar.gz | 742 KB | Debug 符号包 |

## 注意事项

- libusbmuxd 2.x 依赖 libimobiledevice-glue（1.x 版本不依赖）
- pkg-config 名为 `libusbmuxd-2.0`

---
**编译结束**: 2026-05-20 16:15
**最终状态**: published
