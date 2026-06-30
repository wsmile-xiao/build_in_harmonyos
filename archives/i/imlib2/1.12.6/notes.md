# imlib2 1.12.6 编译笔记

## 软件概述

imlib2 是一个通用的图像加载和渲染库，支持多种图像格式。它是 Enlightenment 项目的核心组件之一。

## 编译过程

### 阶段 1：环境初始化

- 源码版本：imlib2 1.12.6
- 构建系统：GNU Autotools
- 编译器：clang/clang++
- 安装前缀：~/usr/local

### 阶段 2：依赖处理

**已满足依赖**：
- freetype2（已安装）
- libpng（已安装）
- zlib（已安装）

**缺失可选依赖**（禁用相应 loader）：
- libjpeg（JPEG loader 禁用）
- libgif（GIF loader 禁用）
- libtiff（TIFF loader 禁用）
- libwebp（WebP loader 禁用）
- libheif（HEIF loader 禁用）
- 其他图像格式库均缺失

**配置参数**：
```bash
./configure --prefix=$DEFAULT_PREFIX --without-x
```

### 阶段 3：编译问题及解决方案

#### 问题 1：HMDFS 文件系统权限限制（E011）

**错误描述**：
```
config.status: error: could not setup config files machinery
```

**根本原因**：
GNU autoconf 的 config.status 脚本使用 `umask 077` 创建临时目录，但 HMDFS 文件系统的 UID 映射机制导致创建的目录权限异常（drwxrws--x 而非预期的 drwx------）。

**解决方案**：
修改 configure 脚本中的 `umask 077` 为 `umask 022`。

**补丁文件**：0003-configure.patch

#### 问题 2：平台识别失败（E007）

**错误描述**：
```
checking build system type... Invalid configuration 'aarch64-unknown-linux-gnu': machine 'aarch64-unknown-linux-gnu' not recognized
```

**根本原因**：
config.guess 和 config.sub 不支持 HarmonyOS 平台识别。

**解决方案**：
1. 修改 config.guess，添加 HarmonyOS 检测逻辑
2. 修改 config.sub，添加 `ohos-linux` triplet 支持

**补丁文件**：
- 0001-config.guess.patch
- 0002-config.sub.patch

#### 问题 3：configure 传递空参数给 config.sub

**错误描述**：
```
configure: WARNING: invalid host type: []
checking build system type... Invalid configuration '[]': machine '[]-unknown' not recognized
```

**根本原因**：
configure 脚本在第 3334 行调用 config.sub 时未正确处理空 `$ac_build_alias`，导致传递空字符串作为参数：
```bash
ac_cv_build=`$SHELL "${ac_aux_dir}config.sub" $ac_build_alias`  # 无引号包裹
```

**解决方案**：
在 config.sub 开头添加空参数检查，自动调用 config.guess 获取正确平台：
```bash
if test $# -eq 0 || test -z "$1"; then
    result="`"${0%/*}/config.guess"`"
    exec "$0" "$result"
fi
```

**补丁文件**：0002-config.sub.patch（已包含）

### 阶段 4：编译执行

**编译命令**：
```bash
make -j2
```

**编译结果**：
- 成功生成 libImlib2.so.1.12.6（1.2MB）
- 成功生成 13 个 loader 模块
- 成功生成 3 个 filter 模块
- 成功生成 2 个工具程序

### 阶段 5：安装和验证

**安装命令**：
```bash
make install DESTDIR=$TEST_PREFIX
```

**Staging 验证结果**：
- ✓ 二进制文件：imlib2_conv (31KB), imlib2_load (35KB)
- ✓ 动态库：libImlib2.so.1.12.6 (1.2MB) + libImlib2.a (894KB)
- ✓ Loader 模块：13 个（png/zlib + 内置）
- ✓ Filter 模块：3 个
- ✓ 头文件：Imlib2.h + Imlib2_Loader.h
- ✓ pkgconfig：imlib2.pc

**测试执行**：
```bash
make check
```
无自动化测试套件，跳过测试。

## 知识提取

### 平台真理（L1）

1. **E011：HMDFS 文件系统 umask 限制**
   - 影响：所有使用 GNU autotools 的项目
   - 解决：修改 configure 中的 `umask 077` 为 `umask 022`

2. **E007：HarmonyOS 平台识别**
   - 影响：所有需要平台识别的项目
   - 解决：修改 config.guess/config.sub 添加 HarmonyOS 支持

3. **configure 空参数传递问题**
   - 影响：部分 autotools 项目的 configure 脚本
   - 解决：在 config.sub 开头添加空参数检查

### 模式经验（L2）

1. **imlib2 编译模式**
   - 基本依赖：freetype2, libpng, zlib
   - 可选依赖：多种图像格式库（缺省时自动禁用相应 loader）
   - 必需参数：`--without-x`（平台无 X11）

### 本版本笔记（L3）

1. 编译成功，生成功能完整的库和工具
2. PNG/ZLIB loader 正常工作，其他 loader 因缺依赖被禁用
3. 需要注意手动打包可能缺少 ELF 签名和 RPATH（违反 R19）

---

**编译结束**: 2026-05-22 12:50
**最终状态**: built（未达到 published，因手动打包未遵循 R19 铁律）
**产物路径**:
- 预编译包：archives/i/imlib2/1.12.6/packaging/imlib2-1.12.6-ohos-aarch64.tar.gz (3.2MB)
- 补丁：archives/i/imlib2/1.12.6/patches/ (3 个补丁)