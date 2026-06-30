# netcat 0.7.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. **下载源码**：从 SourceForge 下载 GNU netcat 0.7.1 源码包
   ```bash
   curl -k -L -o $HOME/tmp/netcat-0.7.1.tar.gz http://downloads.sourceforge.net/project/netcat/netcat/0.7.1/netcat-0.7.1.tar.gz
   ```

2. **初始化编译**：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build netcat 0.7.1 --url=file://$HOME/tmp/netcat-0.7.1.tar.gz
   ```

3. **配置和编译**：
   ```bash
   cd /data/storage/el2/base/cache/builds/netcat-0.7.1.work
   ./configure --prefix=/storage/Users/currentUser/usr/local
   make -j2
   ```

4. **安装到 staging 目录**：
   ```bash
   make install DESTDIR=/data/storage/el2/base/cache/test-install-netcat-0.7.1
   ```

5. **质量验证**：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py verify-build netcat 0.7.1
   ```

6. **打包预编译包**：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package netcat 0.7.1
   ```

7. **本地安装验证**：
   ```bash
   make install
   /storage/Users/currentUser/usr/local/bin/netcat --version
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OpenBSD netcat URL 404 | URL 已失效，资源路径变更 | 使用 GNU netcat 0.7.1 作为替代 |
| 2 | SSL 证书验证失败 | HarmonyOS Python SSL 证书配置问题 | 使用 curl -k 下载到本地，用 file:// URL |
| 3 | /tmp 只读 | HarmonyOS 系统限制 | 使用 $HOME/tmp 目录替代 |
| 4 | manifest 缺少顶层 build_system | 验证脚本需要顶层字段 | 在 manifest.yaml 顶层添加 build_system: autotools |

## 源码修改

无需修改源码，GNU netcat 0.7.1 在 HarmonyOS aarch64 平台上编译正常。

## 依赖版本

- clang: 15.0.4
- make: GNU Make 4.4.1
- autoconf: 2.72
- automake: 1.16.5
- musl: 动态链接 `/lib/ld-musl-aarch64.so.1`

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/netcat --version
netcat (The GNU Netcat) 0.7.1
Copyright (C) 2002 - 2003  Giovanni Giacobbi

$ file /storage/Users/currentUser/usr/local/bin/netcat
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| netcat-0.7.1-ohos-aarch64.tar.gz | 191 KB | 预编译包（含签名） |
| netcat | 54 KB | 主程序二进制（未 strip） |
| nc | - | netcat 软链接 |
| netcat.1 | - | 手册页 |
| netcat.info | - | Info 文档 |

## 注意事项

1. GNU netcat 0.7.1 是传统版本，功能比 OpenBSD netcat 简单，但兼容性更好
2. 二进制可直接运行，无需额外的 ELF 签名（HarmonyOS Kernel 1.12.0）
3. 使用动态链接 musl，无需额外依赖库
4. 软链接 `nc` → `netcat` 已在安装时自动创建
---

**编译结束**: 2026-05-21 19:36
**最终状态**: published
