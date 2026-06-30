# Build Notes — daq 3.0.27 for HarmonyOS

## 基本信息
- **软件**: daq (libdaq) 3.0.27
- **构建系统**: autotools
- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS)
- **编译器**: clang 15.0.4 / clang++ 15.0.4 (OHOS SDK)
- **构建日期**: 2026-05-26

## 构建过程

### 1. 源码准备
- 源码 URL: https://github.com/X0rgDAQ/DAQ/archive/refs/tags/v3.0.27.tar.gz
- SHA256: f499d34487c038c1a9690d300f28c7df43c866569d002a898df87e9c888c0708
- 解压到 `.orig` (原始) 和 `.work` (工作) 目录

### 2. autoreconf
- 需要先运行 `autoreconf -ivf` 生成 configure 脚本
- 需要在 m4/ 目录中添加 pkg.m4 (从 pkg-config 安装路径复制)
- 需要创建 autoconf 符号链接: `/storage/Users/currentUser/usr/local/bin/autoconf -> /data/service/hnp/bin/autoconf`

### 3. 配置修复
- **config.guess/config.sub OHOS 补丁**: 使用 `patch-autotools-ohos.pl` 脦丁，使系统能识别 HarmonyOS
- **config.sub linux-ohos 验证**: 在 `case $kernel-$os-$obj` 行添加 `linux-ohos*-`
- **HMDFS umask 问题**: config.status 中 `umask 077 && mktemp -d` 创建的临时目录在 HMDFS 上无法写入文件，需改为 `umask 000`

### 4. Configure 选项
```bash
TMPDIR=/storage/Users/currentUser/tmp ./configure \
  --prefix=/storage/Users/currentUser/usr/local \
  --disable-pcap-module
```

### 5. 禁用模块说明
- **pcap 模块**: 通过 `--disable-pcap-module` 显式禁用
- **bpf 模块**: 自动禁用（需要 libpcap）
- **dump 模块**: 自动禁用（需要 libpcap）
- 原因: libpcap 预编译包(cmd-pkgs)下载文件为空壳/损坏(10KB全零数据)

### 6. 编译结果
- **共享库**: libdaq.so.3.0.0, libdaq.so.3, libdaq.so
- **静态库**: libdaq.a
- **DAQ 模块（共享）**: daq_afpacket.so, daq_fst.so, daq_savefile.so, daq_trace.so, daq_gwlb.so
- **DAQ 模块（静态）**: libdaq_static_afpacket.a, libdaq_static_fst.a, libdaq_static_savefile.a, libdaq_static_trace.a, libdaq_static_gwlb.a
- **头文件**: daq.h, daq_common.h, daq_dlt.h, daq_module_api.h, daq_version.h
- **pkg-config**: libdaq.pc, 各模块 .pc 文件
- **测试程序**: daqtest, daqtest-static

### 7. 编译警告
- 多个 cast-align 警告（uint8_t* 转换为结构体指针），不影响功能
- format-nonliteral 警告（daq_mod_ops.c），不影响功能

## HMDFS 特殊注意事项
1. `/tmp` 目录不可写，需设置 `TMPDIR=/storage/Users/currentUser/tmp`
2. `umask 077` 创建的目录在 HMDFS 上无法写入文件（Permission denied），需改为 `umask 000`
3. HMDFS 软链接不能 `ln -sf` 覆盖
---

**编译结束**: 2026-05-26 16:02
**最终状态**: published
