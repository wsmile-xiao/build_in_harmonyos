# jq 1.7.1 鸿蒙系统适配指南

> **版本**: 1.0 | **更新日期**: 2026-03-22 | **状态**: ✅ 已验证

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | jq 1.7.1 |
| 目标平台 | HarmonyOS aarch64 (musl libc) |
| 编译器 | Clang 15.0.4 |
| 适配复杂度 | 🟢 低（2 个补丁，仅修改 config 文件） |

## 快速开始

```bash
# 1. 环境准备
export TMPDIR=$HOME/tmp && mkdir -p $TMPDIR
export CC=clang CFLAGS="-fPIC -O2"

# 2. 下载源码
curl -L -o jq-1.7.1.tar.gz https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-1.7.1.tar.gz
tar -xzf jq-1.7.1.tar.gz && cd jq-1.7.1

# 3. 应用补丁
PATCHDIR=/storage/Users/currentUser/tmp/opendesk/build_in_harmonyos/archives/j/jq/1.7.1/patches
patch -p1 < $PATCHDIR/0001-config-guess-harmonyos-support.patch
patch -p1 < $PATCHDIR/0002-config-sub-harmonyos-support.patch

# 4. 配置与编译
./configure --prefix=$HOME/usr/local --without-oniguruma
make -j$(nproc)

# 5. 安装
make install

# 6. 验证
jq --version
```

## 补丁说明

### 0001-config-guess-harmonyos-support.patch

修改 `config/config.guess`，添加 HarmonyOS 系统识别：

1. **LIBC 检测分支**：在 `case $UNAME_SYSTEM` 中添加 `HarmonyOS) LIBC=musl ;;`
2. **系统识别分支**：添加 `aarch64:HarmonyOS:*:*)` 返回 `aarch64-unknown-linux-ohos`

### 0002-config-sub-harmonyos-support.patch

修改 `config/config.sub`，添加 linux-ohos 三元组支持：

1. **maybe_os 分支**：添加 `ohos-linux` 识别
2. **kernel-os 验证**：添加 `linux-ohos*` 支持
3. **OS 列表**：添加 `ohos*` 作为有效操作系统

## 测试验证

```bash
$ jq --version
jq-1.7.1

$ echo '{"name": "test", "value": 123}' | jq '.name'
"test"

$ echo '[1, 2, 3, 4, 5]' | jq 'map(. * 2)'
[2, 4, 6, 8, 10]
```

## 可选：启用 oniguruma

如需正则表达式支持，先编译 oniguruma：

```bash
# 下载 oniguruma
curl -L -o onig-6.9.8.tar.gz https://github.com/kkos/oniguruma/releases/download/v6.9.8/onig-6.9.8.tar.gz
tar -xzf onig-6.9.8.tar.gz && cd onig-6.9.8

# 编译安装
./configure --prefix=$HOME/usr/local
make -j$(nproc) && make install

# 重新编译 jq（启用 oniguruma）
cd ../jq-1.7.1
./configure --prefix=$HOME/usr/local --with-oniguruma=$HOME/usr/local
make -j$(nproc) && make install
```

---

*维护者: OpenHarmony 社区*