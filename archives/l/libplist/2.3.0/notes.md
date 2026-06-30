# libplist 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang
- 状态: published

## 编译步骤

1. 下载源码
   ```bash
   curl -k -L -o libplist-2.3.0.tar.bz2 \
     "https://github.com/libimobiledevice/libplist/releases/download/2.3.0/libplist-2.3.0.tar.bz2"
   tar -xjf libplist-2.3.0.tar.bz2
   ```

2. Configure
   ```bash
   export CC=clang
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

## 源码修改

无补丁，仅修改生成的 config.status 文件（临时）

## 依赖版本

无外部依赖（基础库）

## 验证结果

```bash
pkg-config --modversion libplist-2.0
# 输出: 2.3.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libplist-2.3.0-ohos-aarch64.tar.gz | 2.4 MB | 预编译包 |
| libplist-2.3.0-ohos-aarch64-debug.tar.gz | 2.6 MB | Debug 符号包 |

## 注意事项

- pkg-config 名为 `libplist-2.0`，不是 `libplist`
- Python bindings 可通过 `PYTHON=/bin/false PYTHON_NOVERSIONCHECK=yes` 禁用

---
**编译结束**: 2026-05-20 16:15
**最终状态**: published
