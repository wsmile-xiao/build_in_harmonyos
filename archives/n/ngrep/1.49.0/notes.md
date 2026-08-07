# ngrep 1.49.0 编译笔记

## 编译信息

- **软件名称**: ngrep
- **版本**: 1.49.0
- **编译日期**: 2026-05-26
- **构建系统**: autotools

## 编译过程

### 1. 源码获取

由于 SSL 证书问题，直接从 GitHub 下载失败。最终通过 GitHub API tarball 成功下载：
```
URL: https://api.github.com/repos/jpr5/ngrep/tarball/v1.49.0
大小: 305754 bytes
```

### 2. 平台适配

**config.guess 问题**：
- 原始 config.guess 无法识别 HarmonyOS 系统
- 错误信息：`config.guess: unable to guess system type`
- 解决方案：复制已编译软件（pcre2-10.45）的 config.guess/config.sub
- 识别结果：`aarch64-unknown-linux-ohos`

### 3. 配置选项

```bash
./configure --prefix=$DEFAULT_PREFIX --enable-pcre2 --enable-ipv6
```

配置结果：
- IPv6 支持已启用
- PCRE2 正则库已启用
- libpcap 找到：`/storage/Users/currentUser/usr/local/include`
- pcre2-config 找到：`/storage/Users/currentUser/usr/local/bin/pcre2-config`

### 4. 编译

```bash
make -j2
```

编译成功，无错误。生成的二进制：
- 大小：586360 bytes
- 格式：ELF 64-bit LSB arm64, dynamic linking
- 已 stripped

### 5. 安装

```bash
make install DESTDIR=$TEST_PREFIX
make install  # 本地安装
```

### 6. ELF 签名

鸿蒙系统要求 ELF 二进制必须签名才能执行。使用 `ohc-run.py sign-elf` 完成签名。

### 7. 验证

```bash
$ ngrep -V
ngrep: V1.49.0, libpcap version 1.10.5 (with TPACKET_V3)
```

## 依赖情况

**构建依赖**:
- libpcap 1.10.6（已安装）
- pcre2 10.40（已安装）

**运行依赖**:
- libc.so（仅此一项，libpcap 和 pcre2 静态链接）

## 注意事项

1. ngrep 需要 root 权限或网络捕获能力才能捕获网络数据包
2. 静态链接 libpcap/pcre2 使得预编译包更易于部署
3. 无测试套件（options="!check" 在 Alpine APKBUILD 中）

## 下一步

- 创建预编译包
- 完成质量门禁验证
---

**编译结束**: 2026-08-07 05:20
**最终状态**: built
