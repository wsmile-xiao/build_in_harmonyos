# TiMidity++ 2.13.2 编译笔记

## 编译日期
2026-06-05

## 编译环境
- 目标平台: HarmonyOS (HongMeng Kernel 1.12.0)
- 架构: aarch64
- 编译器: clang (/data/service/hnp/bin/clang)
- 构建系统: autotools

## 编译流程

### 1. 源码获取
- 源码来源: SourceForge 官方 TiMidity++ 项目
- 下载地址: https://sourceforge.net/projects/timidity/files/TiMidity%2B%2B/TiMidity%2B%2B-2.13.2/TiMidity%2B%2B-2.13.2.tar.gz/download
- 说明: 使用 SourceForge 官方 release tarball，符合 R39 官方源要求

### 2. 平台适配问题

#### 问题 E007: config.guess 无法识别 HarmonyOS
**症状**:
```
checking build system type... autoconf/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

**原因**:
旧的 config.guess (timestamp='2003-05-22') 无法识别 HarmonyOS 系统。

**解决方案**:
修改 `autoconf/config.guess` 和 `autoconf/config.sub` 文件：

1. **config.guess 修改**:
   - 在 `arm*:Linux:*:*` 后添加 `aarch64:Linux:*:*` 和 `aarch64:HarmonyOS:*:*` 识别
   - 输出格式: `aarch64-unknown-linux-gnu`

2. **config.sub 修改**:
   - 在 CPU 类型列表中添加 `aarch64` 和 `aarch64-*`
   - 在操作系统列表中添加 `-harmonyos*`

**补丁文件**:
- `patches/0001-config.guess-harmonyos.patch`
- `patches/0002-config.sub-harmonyos.patch`

### 3. HMDFS 文件系统权限问题

#### HMDFS SELinux 权限限制
**症状**:
```
./config.status[931]: can't create ./confstateekbdc/out: Permission denied
```

**原因**:
HMDFS 文件系统的 hmmac 强制访问控制（SELinux）限制 autotools 创建临时文件。

**解决方案**:
通过 `patches/0003-configure-hmdfs-umask.patch` 将 configure 创建临时目录时的 umask 从 077 调整为 022，并在 `/data/storage/el2/base/cache` 目录下编译：
```bash
mkdir -p /data/storage/el2/base/cache/timidity-build
cd /data/storage/el2/base/cache/timidity-build
# 在此目录下执行 configure、make、make install
```

### 4. 编译器配置
系统使用 clang 编译器（位于 `/data/service/hnp/bin/clang`）：
```bash
export CC=/data/service/hnp/bin/clang
export CFLAGS="-O2 -pipe"
```

### 5. 编译选项
由于是命令行编译，禁用所有图形界面和音频播放功能：
```bash
./configure \
  --prefix=$DEFAULT_PREFIX \
  --without-x \
  --enable-audio=no \
  --disable-ncurses \
  --disable-slang \
  --disable-motif \
  --disable-tcltk \
  --disable-emacs \
  --disable-vt100 \
  --disable-xaw \
  --disable-xskin \
  --disable-gtk \
  --enable-server=no
```

### 6. 编译结果

#### 编译成功
- 编译过程顺利完成，生成 timidity 可执行文件
- 编译警告: 6 个警告（主要是代码风格和隐式函数声明）
- 测试: make check 无实际测试

#### 安装成功
- Staging 安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
- 二进制文件大小: 975K (未 strip)
- 依赖库: libc.so (musl)

#### ELF 签名
使用 `ohc-run.py sign-elf` 对二进制文件签名，使其可在 HarmonyOS 上执行。

#### 功能验证
```bash
$ timidity --version
TiMidity++ version 2.13.2
```

## 遇到的问题及解决方案总结

| 问题编号 | 类型 | 解决方案 |
|---------|------|---------|
| E007 | 平台识别 | 修改 config.guess/config.sub |
| E009 | 链接错误 | 添加 -fcommon 编译选项解决 clang/ld.lld 重复符号错误 |
| HMDFS 权限 | 文件系统 | 通过补丁调整 umask，并在 /data/storage/el2/base/cache 编译 |
| 编译器缺失 | 环境配置 | 使用 clang 编译器 |

## 质量门禁检查结果

### G0: 干净构建验证
- **状态**: 需要进一步验证
- **说明**: 补丁已生成，需要验证补丁自包含性

### G1: 二进制完整性
- **状态**: PASS
- **结果**: timidity 可执行文件已生成（975K）

### G2: 功能可用性
- **状态**: PASS
- **结果**: timidity --version 可以运行并显示版本信息

### G3: 可移植性
- **状态**: PASS
- **结果**:
  - ELF 签名完成
  - 依赖: libc.so (musl)
  - 动态链接器: /lib/ld-musl-aarch64.so.1

### G4: 档案完整性
- **状态**: PARTIAL
- **结果**:
  - 补丁文件已生成
  - manifest.yaml 已创建
  - notes.md 已创建
  - 缺少预编译包（待生成）

## 知识提取记录

### E007: config.guess 平台不识别
**适用场景**: 任何使用 autotools 构建系统的软件在 HarmonyOS 上编译
**解决方案**: 在 config.guess 和 config.sub 中添加 HarmonyOS 识别
**补丁模板**: 参考 patches/0001-*.patch 和 patches/0002-*.patch

### HMDFS 权限限制问题
**适用场景**: HMDFS 文件系统上执行 autotools 构建
**解决方案**: 通过补丁调整 configure 的临时目录 umask，并在 `/data/storage/el2/base/cache` 目录下编译
**关键环境变量**: `TMPDIR=/data/storage/el2/base/cache`

### E009: clang/ld.lld 重复符号链接错误
**适用场景**: 老旧 C 项目（2004 年前后）使用 clang/ld.lld 编译链接
**问题**: TiMidity++ 2.13.2 源码中多个 .c 文件对同名全局变量有临时定义（tentative definition），依赖旧版 GCC `-fcommon` 行为允许合并。clang 15 / ld.lld 默认 `-fno-common`，导致 `duplicate symbol` 链接错误
**涉及符号**: `insertion_effect_gs`、`reverb_status_xg`、`chorus_status_gs`、`delay_status_gs`、`global_pink_noise_light` 等
**解决方案**: 在 conanfile.py 的 generate() 中通过 `tc.cflags.append("-fcommon")` 启用 common 语义
**通用性**: 该修复适用于所有依赖 `-fcommon` 的老项目

## 后续建议

1. **预编译包生成**: 需要创建 tar.gz 预编译包供用户安装
2. **配置文件**: timidity 需要 timidity.cfg 配置文件和音色库才能播放 MIDI
3. **文档完善**: 补充软件级 README.md

---
**编译结束**: 2026-06-05 17:10:00
**最终状态**: built (编译成功，待打包发布)
