# libsigrok 0.5.2 构建笔记

## 构建日期
2026-06-08

## 构建环境
- 系统: OpenHarmony (HMDFS文件系统)
- 架构: aarch64 (ARM64)
- 编译器: clang-15
- 构建工具: autotools (autoconf-2.72, automake-1.16)

## 源码来源
libsigrok-libsigrok-0.5.2 (GitHub release)
目录: ~/libsigrok-libsigrok-0.5.2

## 构建过程

### 1. 源码准备
源码已解压到 ~/libsigrok-libsigrok-0.5.2

### 2. 构建系统修复

#### 问题1: 缺少预生成的configure脚本
**症状**: 源码目录缺少configure脚本，只有configure.ac
**解决**: 运行autoreconf -fi生成configure脚本

#### 问题2: 缺少pkg.m4宏文件
**症状**: autogen.sh失败，报错"possibly undefined macro: PKG_CHECK_MODULES"
**解决**: 手动创建完整的pkg.m4文件到m4/目录
- 内容来源: pkg-config官方源码的pkg.m4文件
- 关键宏: PKG_PROG_PKG_CONFIG, PKG_CHECK_MODULES, PKG_CHECK_EXISTS等
- 文件位置: ~/libsigrok-libsigrok-0.5.2/m4/pkg.m4

#### 问题3: HMDFS文件系统不支持硬链接
**症状**: libtool编译时报错"ln: cannot create hard link... Operation not permitted"
**解决**: 修改libtool脚本，将硬链接改为文件复制
- 修改位置: libtool脚本第11463行
- 修改内容: `func_show_eval "ln $obj $gentop/$newobj || cp $obj $gentop/$newobj"`
           改为 `func_show_eval "cp $obj $gentop/$newobj"`
- 同时修改: autostuff/ltmain.sh (备用)

#### 问题4: 缺少libzip.so符号链接
**症状**: 链接时报错"ld.lld: error: unable to find library -lzip"
**解决**: 创建libzip.so符号链接
- libzip库已存在: ~/usr/local/lib/libzip.so.5.5
- 创建链接: ln -sf libzip.so.5.5 libzip.so

#### 问题5: 缺少libffi.so符号链接
**症状**: 编译时报错找不到libffi.so
**解决**: 创建libffi.so符号链接
- libffi库位置: ~/usr/local/lib/external/libffi.so
- 创建链接: ln -sf external/libffi.so libffi.so

### 3. 构建步骤

```bash
# 设置TMPDIR避免HMDFS SELinux问题
export TMPDIR=/data/storage/el2/base/cache

# 设置PKG_CONFIG_PATH
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

# 生成configure脚本
autoreconf -fi

# 配置
./configure --prefix=/storage/Users/currentUser/usr/local

# 编译
make -j2

# 安装
make install

# 安装到临时目录（用于打包）
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libsigrok-0.5.2
```

### 4. 验证结果

```bash
# pkg-config验证
pkg-config --modversion libsigrok
# 输出: 0.5.2

# 库文件验证
ls ~/usr/local/lib/libsigrok.*
# 输出: libsigrok.so, libsigrok.so.4, libsigrok.so.4.1.1, libsigrok.a

# 库大小
ls -lh ~/usr/local/lib/libsigrok.so.4.1.1
# 输出: 3.7M
```

## 构建结果

### 成功
- ✅ configure脚本成功生成
- ✅ 编译通过（无硬链接错误）
- ✅ 库文件安装成功
- ✅ pkg-config能识别libsigrok
- ✅ 预编译包创建成功

### 预编译包信息
- 文件名: libsigrok-0.5.2-ohos-aarch64.tar.gz
- 大小: 12MB
- 内容: lib/, include/, share/

### 已启用的驱动（部分）
- demo
- fx2lafw
- saleae-logic16
- saleae-logic-pro
- rigol-ds
- siglent-sds
- agilent-dmm
- fluke-dmm
- uni-t-dmm
- 等60+驱动

### 未启用的驱动（缺少依赖）
- chronovu-la (missing libftdi)
- ftdi-la (missing libftdi)
- hp-3478a (missing libgpib)
- 等

## 关键解决方案总结

1. **手动创建pkg.m4文件**
   - 从pkg-config源码获取完整的pkg.m4宏定义
   - 放置到m4/目录
   - 解决autoreconf失败问题

2. **修改libtool避免硬链接**
   - HMDFS文件系统不支持跨设备硬链接
   - 将libtool中的`ln`改为`cp`
   - 解决"Operation not permitted"错误

3. **创建缺失的符号链接**
   - libzip.so -> libzip.so.5.5
   - libffi.so -> external/libffi.so

4. **设置TMPDIR环境变量**
   - TMPDIR=/data/storage/el2/base/cache
   - 避免HMDFS SELinux权限问题

## 构建时间
约20分钟（包括配置、编译、安装）

## 后续建议

### 如果需要C++绑定（PulseView等）
需要安装以下依赖：
- glibmm
- Doxygen
- PyGObject
- SWIG

### 如果需要更多硬件驱动
需要安装以下依赖：
- libftdi1 (用于FTDI设备)
- libgpib (用于GPIB设备)
- libieee1284 (用于并行端口设备)

## 文件位置

### 源码目录
~/libsigrok-libsigrok-0.5.2

### 安装目录
~/usr/local

### 临时安装目录（用于打包）
~/tmp/test-install-libsigrok-0.5.2

### 归档目录
~/archive/libsigrok-0.5.2/

### 预编译包
~/libsigrok-0.5.2-ohos-aarch64.tar.gz

## 参考资料
- libsigrok官方文档: https://sigrok.org/wiki/Libsigrok
- pkg-config文档: https://www.freedesktop.org/wiki/Software/pkg-config/
- autotools文档: https://www.gnu.org/software/automake/manual/