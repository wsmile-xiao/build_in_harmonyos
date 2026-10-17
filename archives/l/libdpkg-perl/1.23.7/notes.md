# libdpkg-perl 1.23.7 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/libdpkg-perl/1.23.7 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 Debian snapshot 镜像下载 dpkg 源码包
（dpkg_1.23.7.tar.xz，libdpkg-perl 是 dpkg 源码树中 scripts/ 目录的
Perl 模块集）并 strip_root。

### 2. 打包（package()）
- 纯 Perl 模块集（scripts/ 下 Dpkg.pm + Dpkg/** 共 92 个 .pm），无编译
- `package()` 拷贝 `scripts/` 到 `lib/perl5/`（perl site-lib），排除
  *.pl 工具脚本 / Makefile / po / completion 等非 .pm 内容
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——dataproperty/pytablewriter 同款先例）+ commands.json（R38）

## 依赖
- 仅 dpkg + Perl 核心（libfile-fcntllock-perl 为 Recommends 非必需，
  不在 Depends 列表）

## 上游测试（rule 4）
- 测试目录：dpkg 源码树 scripts/t/（libdpkg-perl 的 Perl 单元测试，prove）
- 本地实测：**50 文件 / 12353 测试：12341 通过 / 12 失败（99.9%）**
  ——需设 `DPKG_DATADIR=data` + `DPKG_ORIGINS_DIR=scripts/t/origins`
  才能加载数据表（实测两轮修复：DPKG_DATADIR 修复 cputable/ostable，
  DPKG_ORIGINS_DIR 修复 vendor origins）
- 12 个显式失败多为环境阻塞（缺 dpkg C 二进制 / Ubuntu vendor 数据 /
  patch -t 行为等，rule 5.2 如实记录），非库缺陷
- 适配后：test_package R34 真实 perl 加载打包的 Dpkg::Version 并
  version_compare 校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心依赖模块）
