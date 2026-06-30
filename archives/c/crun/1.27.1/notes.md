# crun 1.27.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 下载源码包 crun-1.27.1.tar.gz
2. 解压到 ~/builds/crun-1.27.1.work
3. 运行 configure:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --enable-embedded-yajl --disable-caps --disable-seccomp --disable-systemd --disable-bpf
   ```
4. 编译: `make -j2`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 质量修复:
   - 使用 patchelf 设置 RPATH
   - 使用 strip 清除符号
   - 尝试 ELF 签名（平台限制）
7. 手动打包（因 tar 命令限制）:
   ```bash
   python3 -c "import tarfile; ..."
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | argp_parse undefined | libargp.a 依赖 libintl | 已安装 argp-standalone + libintl |
| 2 | 无 RPATH | 动态库 libintl.so.8 找不到 | patchelf --set-rpath |
| 3 | 未 strip | 符号表过大 | strip 命令 |
| 4 | ELF 未签名 | 鸿蒙平台要求 | binary-sign-tool（需信任证书） |
| 5 | tar 路径过长 | ustar 格式限制 | Python tarfile 模块 |

## 源码修改

19个补丁文件（自动生成）:
- 平台适配: config.guess/config.sub（识别 OHOS）
- 构建工具: install-sh/depcomp/missing（兼容鸿蒙）
- libtool: ltmain.sh/libtool.m4（动态链接适配）

## 依赖版本

- argp-standalone: 1.5.0（静态库）
- libintl: 0.21（动态库 libintl.so.8）

## 验证结果

```bash
# 二进制信息
file ~/usr/local/bin/crun
# ELF shared object, 64-bit LSB arm64, dynamic, stripped

# RPATH
readelf -d ~/usr/local/bin/crun | grep RUNPATH
# Library runpath: [/storage/Users/currentUser/usr/local/lib]

# 功能测试
~/usr/local/bin/crun --version
# crun version 1.27.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| crun-1.27.1-ohos-aarch64.tar.gz | 698K | 预编译包 |
| bin/crun | 1.0M | 主程序（stripped, RPATH） |
| lib/libcrun.a | 2.0M | 静态库 |
| lib/libintl-wrapper.a | 1.1K | libintl wrapper |

## 注意事项

⚠️ ELF 签名是鸿蒙平台硬性要求，但签名工具需要信任证书，本次编译因平台限制未能完成签名，状态标记为 built（而非 published）。

⚠️ tar 命令存在路径长度限制，使用 Python tarfile 模块绕过。

---
**编译结束**: 2026-05-27 15:01
**最终状态**: built
---

**编译结束**: 2026-05-27 15:03
**最终状态**: built
