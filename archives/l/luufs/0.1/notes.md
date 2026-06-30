# luufs 0.1 编译笔记

## 编译信息
- 开始时间: 2026-05-27
- 结束时间: 2026-05-27
- 构建系统: Makefile（简单单文件项目）
- 依赖: FUSE 2.9.9, zlib 1.3.1

## 编译过程

### Step 1: 环境初始化
- 手动下载源码（SSL 证书问题，使用 curl -k 跳过验证）
- 解压到 ~/tmp/builds/luufs-0.1.work
- 手动创建编译上下文（.build-context-luufs-0.1）
- 设置 PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig

### Step 2: 编译问题与解决

#### 问题：链接错误 - pthread 符号未定义
```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_cancel
>>> referenced by /storage/Users/currentUser/usr/local/lib/libfuse.so
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: pthread_setcancelstate
>>> referenced by /storage/Users/currentUser/usr/local/lib/libfuse.so
```

#### 原因分析
- 链接器使用了 `--no-allow-shlib-undefined` 选项
- 要求动态库的所有未定义符号必须在链接时被满足
- libfuse.so 需要 pthread 符号，但系统使用 musl libc（pthread 已集成到 libc）

#### 解决方案
使用 `-Wl,--allow-shlib-undefined` 选项放宽链接器限制：
```bash
clang -o luufs luufs.o \
  -L$HOME/usr/local/lib \
  -lfuse -lz -lpthread -ldl \
  -Wl,--allow-shlib-undefined \
  -Wl,-rpath,$HOME/usr/local/lib
```

### Step 3: Staging 安装（DESTDIR 模式）
- 创建正确的 staging 目录结构：$TEST_PREFIX/$DEFAULT_PREFIX/
- 安装文件到：sbin/luufs, usr/share/doc/luufs/*, usr/share/man/man8/luufs.8

### Step 4: RPATH 设置
- 添加 `-Wl,-rpath,$HOME/usr/local/lib` 确保运行时能找到 libfuse.so.2
- 使用 `-Wl,--disable-new-dtags` 确保 RPATH 而不是 RUNPATH

### Step 5: 打包
- 质量门禁验证：PASS
- 预编译包：luufs-0.1-ohos-aarch64.tar.gz（361KB）
- Debug 包：luufs-0.1-ohos-aarch64-debug.tar.gz（85KB）

### Step 6: 本地安装验证
- 安装到 ~/usr/local/sbin/luufs
- 运行验证：`~/usr/local/sbin/luufs --help` 正常输出 Usage

## 关键发现

### 链接器模式差异（musl vs glibc）
- 鸿蒙系统使用 musl libc，pthread 功能已集成到 libc
- 不存在独立的 libpthread.so
- 链接器默认使用 `--no-allow-shlib-undefined`，与 glibc 系统不同
- 需要使用 `-Wl,--allow-shlib-undefined` 放宽限制

### Makefile 项目适配
- luufs 使用简单 Makefile，无需 configure
- 需要 pkg-config 查找依赖（FUSE、zlib）
- 安装路径需要调整为 DESTDIR 模式

## 产物清单
- sbin/luufs（可执行文件，43KB）
- usr/share/doc/luufs/README, AUTHORS, COPYING
- usr/share/man/man8/luufs.8

## 功能测试结果（2026-05-27）

### 测试环境
- 平台: OpenHarmony (dev), HongMeng Kernel 1.12.0
- 编译器: clang 15.0.4
- C库: musl libc

### 测试项目

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 二进制完整性 | ✅ 通过 | ELF 64-bit ARM64 动态链接 |
| 依赖库检查 | ✅ 通过 | libfuse.so.2, libc.so，RPATH 正确 |
| 命令行接口 | ✅ 通过 | 正确显示用法说明 |
| 挂载功能 | ❌ 受阻 | 平台限制：无 FUSE 内核支持 |

### 平台限制详情

**FUSE 架构说明**:

FUSE = **用户态工具** + **内核态模块**

| 组成部分 | 作用 | 当前状态 | 来源 |
|----------|------|----------|------|
| fusermount + libfuse.so | 用户态挂载工具和库 | ✅ 已安装 | 本地预编译包 fuse 2.9.9 |
| fuse.ko + /dev/fuse | 内核模块和设备节点 | ❌ 缺失 | 需要 OpenHarmony 内核启用 |

**检查结果**:
```
用户态: fusermount version 2.9.9 ✅
        libfuse.so.2 @ ~/usr/local/lib ✅
内核态: /dev/fuse - Permission denied ❌
        /proc/filesystems - 无 fuse 条目 ❌
```

**结论**: 预编译包仅提供用户态组件（已安装），内核模块缺失无法通过预编译包解决。这是 OpenHarmony 平台限制，需要内核配置启用 FUSE 模块。

**替代验证方案**:
在支持 FUSE 的 Linux 系统上验证：
```bash
# 挂载测试
luufs /path/to/ro /path/to/rw /path/to/target

# 验证挂载
mount | grep luufs
ls /path/to/target

# 卸载
fusermount -u /path/to/target
```

### 部署建议

1. **目标系统要求**: 需启用 FUSE 内核模块
2. **依赖**: fusermount 工具 + libfuse.so.2（已包含在预编译包）
3. **平台适配**: 建议在 OpenHarmony 内核配置中启用 FUSE 模块

### 测试报告路径

`archives/l/luufs/0.1/reports/test-report.md`

---
**编译结束**: 2026-05-27 12:39
**最终状态**: built（成功编译，功能测试受阻于平台限制）
**产物路径**: archives/l/luufs/0.1/packaging/luufs-0.1-ohos-aarch64.tar.gz
**测试报告**: archives/l/luufs/0.1/reports/test-report.md
