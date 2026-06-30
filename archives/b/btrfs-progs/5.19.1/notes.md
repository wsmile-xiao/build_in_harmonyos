# btrfs-progs 5.19.1 编译笔记

## 基本信息
- 软件名: btrfs-progs
- 版本: 5.19.1
- 构建系统: autotools
- 编译日期: 2026-06-16

## 源码信息
- URL: https://mirrors.edge.kernel.org/pub/linux/kernel/people/kdave/btrfs-progs/btrfs-progs-v5.19.1.tar.xz
- 已下载到: ~/tmp/btrfs-progs-v5.19.1.tar.xz
- 解压到: ~/builds/btrfs-progs-5.19.1.work

## 编译过程

### Step 1: 初始化
- 手动下载源码包
- 解压到工作目录

### Step 2: 编译（已完成）
- **应用 E011 方案**: 修改 configure 中 `umask 077` 为 `umask 022`
- **更新 config.guess/config.sub**: 使用预编译版本识别 OpenHarmony 平台
- **configure 参数**: --prefix=$DEFAULT_PREFIX --disable-documentation --disable-libudev --disable-python --disable-lzo --disable-convert
- **依赖处理**:
  - ext2fs (uuid/blkid): 已安装，通过 EXTRA_CFLAGS 添加头文件路径
  - zstd: 已安装
  - pthread: 创建 pthread-stubs.c stub 函数（pthread_cancel/pthread_setcancelstate/pthread_setcanceltype/pthread_tryjoin_np 不可用）
- **编译成功**: 所有二进制文件已生成

### Step 3: 安装
- make install DESTDIR=$TEST_PREFIX
- 产物位置: ~/tmp/test-install-btrfs-progs-5.19.1/storage/Users/currentUser/usr/local/

### Step 4: 测试
- make check: 无测试目标（旧版本特性）

### 知识提取
- **E011 方案**: 成功应用，解决 HMDFS umask 077 权限问题
- **E007 方案**: 更新 config.guess/config.sub 识别平台
- **E051 方案**: pthread_cancel 等函数不可用，创建 stub 函数解决
- **平台发现**: btrfs-progs 5.19.1 依赖 ext2fs/blkid/uuid/zstd，需确保头文件路径正确
---

**编译结束**: 2026-06-16 18:03
**最终状态**: built
---

**编译结束**: 2026-06-16 18:09
**最终状态**: published
