# kpartx 0.14.3 编译笔记

## 基本信息

- **软件**: kpartx (multipath-tools 子项目)
- **版本**: 0.14.3
- **编译日期**: 2026-06-11

## 编译过程

### 1. 源码获取

kpartx 是 multipath-tools 项目的一部分，源码从 GitHub 获取：
- URL: https://github.com/opensvc/multipath-tools/archive/refs/tags/0.14.3.tar.gz

由于任务要求 0.13.0 版本不存在，使用最新稳定版本 0.14.3。

### 2. 依赖解决

**核心依赖**: libdevmapper (device mapper library)

发现系统中没有 libdevmapper：
1. 预编译包仓库 (cmd-pkgs) 中没有 devmapper/lvm2
2. 要先编译 lvm2 获取 libdevmapper

**编译 libdevmapper (lvm2 v2.03.39)**：
- 从 GitHub 下载 lvm2: https://github.com/lvmteam/lvm2
- 遇到 config.guess 无法识别 HarmonyOS 系统的问题
- 解决方案：手动指定 --build=aarch64-linux-gnu
- 遇到 config.status 临时目录创建权限问题
- 解决方案：修改 config.status 使用固定的 TMPDIR
- 成功编译并安装 libdm 到 ~/usr/local

### 3. kpartx 编译

multipath-tools 使用自定义 Makefile 系统（非 autotools）：
- 运行 `make -f create-config.mk` 生成配置
- 需要设置 CPPFLAGS 和 LDFLAGS 指向 libdevmapper
- 成功编译 kpartx

### 4. 安装与签名

- 安装到 staging 目录: ~/tmp/test-install-kpartx-0.14.3
- 包含: kpartx 二进制、libdevmapper.so.1.02、man page
- 使用 ohc-run.py sign-elf 进行 ELF 签名

## 遇到的问题与解决方案

### 问题 1: SSL 证书验证失败
- **原因**: Python urllib SSL 证书验证失败
- **解决**: 使用 curl -k 手动下载源码

### 问题 2: config.guess 不识别 HarmonyOS
- **原因**: HarmonyOS 是新系统，config.guess 未更新
- **解决**: 手动指定 --build=aarch64-linux-gnu

### 问题 3: config.status 临时目录权限
- **原因**: HMDFS/SELinux 限制子目录创建
- **解决**: 修改 config.status 使用预创建的 TMPDIR

### 问题 4: 缺少 install 命令
- **原因**: toybox 没有 install 命令
- **解决**: 使用 cp 手动复制文件

### 问题 5: 缺少 libudev
- **原因**: 系统没有 libudev
- **解决**: kpartx 编译不需要 libudev 实际功能，仅警告

## 知识提取

### 新发现的错误模式 (待沉淀)

1. **HarmonyOS config.guess 未识别**
   - 现象: `cannot guess build type`
   - 解决: 手动指定 --build=aarch64-linux-gnu

2. **HMDFS config.status 临时目录创建失败**
   - 现象: `can't create ./confXXXXXX/subs1.awk`
   - 解决: 修改 config.status 使用固定 TMPDIR

## 验证结果

- kpartx --version 输出: multipath-tools v0.14.3 (02/05, 2026)
- 基本功能验证: 命令行参数解析正常

## 备注

kpartx 在鸿蒙系统上可能无法完全工作，因为它需要 device-mapper 内核模块支持。
当前编译仅证明可编译性，实际功能依赖于内核模块。