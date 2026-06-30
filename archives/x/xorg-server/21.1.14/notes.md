# xorg-server 21.1.14 编译笔记

## 编译目标
编译 Xorg Server 21.1.14，作为 X Window System 的核心显示服务器。

## 软件信息
- **名称**: xorg-server
- **版本**: 21.1.14
- **源码**: https://xorg.freedesktop.org/archive/individual/xserver/xorg-server-21.1.14.tar.xz
- **构建系统**: autotools

## 编译步骤

### Step 1: 环境准备
- ✅ 设置 TMPDIR=/data/storage/el2/base/cache
- ✅ 下载源码（4.7MB tar.xz）
- ✅ 解压到 ~/tmp/builds/xorg-server-21.1.14.{orig,work}
- ✅ 创建归档目录结构

### Step 2: 依赖检查

#### 已安装依赖（来自 cmd-pkgs）
- xorgproto 2024.1 ✅
- libx11 1.8.10 ✅
- libxext 1.3.6 ✅
- pixman ✅

#### 待检查依赖
- libxcb
- xcb-util
- xcb-proto
- libdrm
- libGL

### Step 3: 配置（待执行）

### Step 4: 编译（待执行）

### Step 5: 质量门禁验证（待执行）

## 平台适配要点
1. OpenHarmony 无内核 DRM/KMS 支持
2. 需要禁用不需要的驱动和功能
3. 可能需要特殊配置选项

## 编译日志
- 2026-05-29 18:58: 开始编译流程