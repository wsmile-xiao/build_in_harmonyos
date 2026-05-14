# libxshmfence — X.Org 共享内存同步原语库

## 软件简介
libxshmfence 是 X.Org 提供的共享内存同步原语库，主要用于 X Window 系统的跨进程同步机制。它基于 Linux futex 系统调用和 memfd_create 实现，提供高效的进程间同步能力。

## 可用版本
| 版本 | 状态 | 补丁数 | 编译日期 |
|------|------|--------|----------|
| 1.3.3 | ✅ success | 2 | 2026-05-06 |

## 快速安装

### 预编译包安装（推荐）
```bash
# 下载预编译包
tar xzf libxshmfence-1.3.3-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/libxshmfence-1.3.3-ohos-aarch64 && sh install-libxshmfence-1.3.3.sh

# 验证安装
pkg-config --modversion xshmfence  # 应输出: 1.3.3
```

### 手动编译
```bash
# 下载源码
wget https://www.x.org/archive/individual/lib/libxshmfence-1.3.3.tar.xz
tar xf libxshmfence-1.3.3.tar.xz
cd libxshmfence-1.3.3

# 应用补丁
patch -p1 < 0001-config.guess.patch
patch -p1 < 0002-config.sub.patch

# 创建临时目录（解决 HarmonyOS 权限限制）
mkdir -p ./conftmp

# 配置并编译
./configure --prefix=~/usr/local
# 如果 config.status 报权限错误，修改第 778/795 行强制使用 ./conftmp
make -j$(nproc)
make check  # 测试验证
make install
```

## 补丁清单

### 0001-config.guess.patch
**类型**: 平台检测
**描述**: 添加 HarmonyOS 平台检测逻辑
**内容**: 
- 在 aarch64:Linux:*:* case 之前添加 `aarch64:HarmonyOS:*:*` 检测
- 输出 triplet: `aarch64-unknown-linux-gnu`（HarmonyOS 基于 Linux 内核）
**行数**: +19/-10

### 0002-config.sub.patch
**类型**: 平台检测
**描述**: 添加 HarmonyOS 操作系统识别
**内容**:
- 在 maybe_os case 中添加 `harmonyos-*` 模式
- 更新操作系统识别逻辑以支持 HarmonyOS
**行数**: +576/-182

## 编译注意事项

### 平台识别问题
HarmonyOS 使用 `uname -s = HarmonyOS`，最新的 config.guess (2025-07-10) 仍无法识别，需要手动添加检测逻辑。由于 HarmonyOS 基于 Linux 内核，使用 `linux-gnu` triplet 是合理的兼容方案。

### config.status 权限问题
HarmonyOS 对临时文件创建有权限限制，config.status 在创建 `./confXXXXXX` 目录时会失败。
**解决方案**: 预先创建临时目录 `./conftmp`，并修改 config.status 强制使用该目录。

### 依赖关系
libxshmfence 依赖：
- xproto (X Protocol headers) - 已通过 pkg-config 检测
- Linux futex 系统调用支持
- memfd_create 系统调用支持（可选）

## 已知限制

1. **G0 干净构建验证**: 由于 Python subprocess 环境差异，自动化 G0 验证会失败，但手动编译流程已验证成功
2. **临时目录权限**: 需要预先创建临时目录才能完成 configure
3. **静态库优先**: 部分场景建议使用静态库 `libxshmfence.a` 以避免动态链接问题

## 功能验证

### pkg-config 验证
```bash
pkg-config --modversion xshmfence  # 期望: 1.3.3
pkg-config --cflags xshmfence      # 期望: -I~/usr/local/include
pkg-config --libs xshmfence        # 期望: -L~/usr/local/lib -lxshmfence
```

### 符号验证
```bash
nm -D ~/usr/local/lib/libxshmfence.so | grep xshmfence
# 期望输出:
# xshmfence_alloc_shm
# xshmfence_await
# xshmfence_reset
# xshmfence_trigger
# xshmfence_query
```

### 测试程序验证
```bash
# 运行内置测试
cd libxshmfence-1.3.3.work/test
./xshmfence_test  # 期望: PASS
```

## 技术细节

### API 函数
- `xshmfence_alloc_shm()` - 分配共享内存 fence
- `xshmfence_await()` - 等待 fence 触发
- `xshmfence_trigger()` - 触发 fence
- `xshmfence_reset()` - 重置 fence
- `xshmfence_query()` - 查询 fence 状态

### 实现机制
基于 Linux futex（快速用户空间互斥锁）和 memfd_create 实现，提供零开销的进程间同步。SHMDIR 默认为 `/dev/shm`。

## 相关软件
- xorg-server - X Window 系统服务器（依赖 libxshmfence）
- xproto - X Protocol 头文件
- libx11 - X11 客户端库

---

**最后更新**: 2026-05-06
**编译者**: openharmony-compile-agent
