# libev 4.33 编译进度记录

## 编译信息
- 软件名: libev
- 版本: 4.33
- 构建系统: autotools（手动编译）
- 编译状态: partial（成功但需记录系统限制）
- 编译日期: 2026-04-25

## 编译过程

### Phase 1: 初始化
- 下载源码: http://dist.schmorp.de/libev/libev-4.33.tar.gz
- 解压成功
- 环境检查通过

### Phase 2: 配置尝试
- 首次尝试: config.guess 无法识别 HarmonyOS 系统
- 修复方法:
  1. 下载最新的 config.guess 和 config.sub（2025-07-10 版本）
  2. 修改 config.guess 添加 aarch64:HarmonyOS 识别（输出 aarch64-unknown-linux-ohos）
  3. 修改 config.sub 添加 ohos-linux 分支和 OS/kernel 白名单

- 二次尝试: config.status 遭遇 HMDFS 文件系统限制
  - 错误: "can't create ./confXXX/subs1.awk: Permission denied"
  - 原因: HMDFS 文系统对 autotools 的临时目录创建有特殊限制
  - 尝试了多种方法（VPATH 构建、不同目录、不同 shell）均失败

### Phase 3: 手动编译
- 由于 autotools 配置失败，采用手动编译方式
- 创建 config.h（基于 configure 输出的宏定义）
- 手动编译源文件:
  - `clang -c -fPIC -O2 -I. ev.c -o ev.o`（40 个警告，均为 assert 语句的兼容性问题）
  - `clang -c -fPIC -O2 -I. event.c -o event.o`
- 创建库文件:
  - 静态库: `llvm-ar rcs libev.a ev.o event.o` (69K)
  - 动态库: `clang -shared -fPIC -o libev.so ev.o event.o` (70K)

### Phase 4: 安装和验证
- 安装到 ~/usr/local:
  - 库文件: libev.a, libev.so
  - 头文件: ev.h, ev++.h, event.h
- 验证测试程序成功运行:
  - 输出 "libev version: 4.33"
  - 成功创建 default loop

### Phase 5: 预编译包创建
- 创建预编译包目录结构
- 由于 tar.gz 在 HMDFS 上有问题，使用 zip 格式
- 预编译包: libev-4.33-ohos-aarch64.zip (73K)

## 遇到的问题和解决方案

### 问题1: config.guess 无法识别 HarmonyOS
- 解决方案: 修改 config.guess 添加 HarmonyOS 识别分支
- 知识沉淀: E007 (config.guess)

### 问题2: config.sub 无法识别 ohos 三元组
- 解决方案: 修改 config.sub 添加 ohos-linux 分支和白名单
- 知识沉淀: E072 (config.sub 三元组验证)

### 问题3: HMDFS 文件系统限制导致 config.status 失败
- 现象: autotools 无法在当前目录创建临时文件
- 原因: HMDFS 的特殊权限限制
- 解决方案: 采用手动编译方式绕过 autotools
- 知识沉淀: 需要记录到 E046 或新建条目

### 问题4: tar.gz 创建失败（ustar header限制）
- 现象: GNU tar 和 toybox tar 都报 "ustar header field is too small"
- 原因: HMDFS 文件系统路径限制
- 解决方案: 使用 zip 格式创建预编译包
- 状态: partial（预编译包可用但格式非标准）

## 补丁文件
- 0001-config.guess.patch: 添加 HarmonyOS 识别
- 0002-config.sub.patch: 添加 ohos 三元组支持

## 后续工作
- 需要记录 HMDFS 限制问题到知识图谱
- 需要研究是否可以修改 autotools 以适应 HMDFS
- 预编译包格式建议改为 zip（或找到 tar.gz 的解决方案）

