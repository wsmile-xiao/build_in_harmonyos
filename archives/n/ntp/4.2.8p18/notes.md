# ntp 4.2.8p18 适配笔记

## 概述
适配 NTP 4.2.8p18 到 OpenHarmony PC (aarch64) 平台。
NTP 是网络时间协议参考实现，包含 ntpq、ntpdate、ntpdc、sntp 等命令行工具。

## 构建系统
- 构建系统: autotools
- 内嵌子项目: libevent, libopts
- 依赖: openssl (可选，使用 --without-crypto 跳过)

## 适配过程

### 1. 初始化
```bash
python3 scripts/ohc-run.py init-build ntp 4.2.8p18 --url=https://downloads.nwtime.org/ntp/4.2.8/ntp-4.2.8p18.tar.gz
```

### 2. 补丁
创建了以下补丁:
- 0001-sntp-libevent-build-aux-config.guess.patch: 添加 HarmonyOS 系统识别
- 0001-sntp-libevent-build-aux-config.sub.patch: 添加 OHOS 三元组支持

### 3. 编译配置
```bash
configure --build=aarch64-linux-gnu --host=aarch64-linux-ohos \
  --enable-local-libopts --enable-local-libevent \
  --without-ntpsnmpd --without-crypto \
  --with-yielding-select=yes --disable-dependency-tracking \
  --with-hardenfile=/dev/null
```

### 4. 关键问题
1. **config.guess/sub 平台识别**: 需要手动添加 HarmonyOS 识别（与 strace 6.19 相同模式）
2. **genHardFlags/genLocInfo 脚本**: 使用 /system/bin/sh 解释器，需改为 /bin/sh
3. **mktemp 缺失**: HarmonyOS 无 mktemp 命令，config.status 需要 mktemp 包装器
4. **umask 077 问题**: HMDFS 上 umask 077 导致 setgid 位阻止写入，需改为 umask 022
5. **源文件属主**: 构建目录文件属主与当前用户不一致，需复制到用户目录后构建

### 5. 产物
预期编译产物:
- ntpq: NTP 查询工具
- ntpdate: NTP 日期设置工具
- ntpdc: NTP 控制工具
- sntp: 简单 NTP 客户端

## 对话记录
- 2026-07-16: 首次适配，configure 通过，make 因权限问题未完成
- 测试环境: HarmonyOS aarch64, clang 15.0.4

## 使用说明
```bash
# 查询 NTP 服务器
ntpq -p

# 设置系统时间
ntpdate pool.ntp.org
```