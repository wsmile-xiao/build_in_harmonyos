# ubertooth 2020-12-R1 编译笔记

## 基本信息
- 软件: ubertooth (Bluetooth experimentation tools)
- 版本: 2020-12-R1
- 构建系统: CMake
- 编译日期: 2026-06-11

## 编译过程

### 初始化
- 源码下载: GitHub tarball (https://github.com/greatscottgadgets/ubertooth/tarball/2020-12-R1)
- 解压目录: ~/tmp/builds/ubertooth-2020-12-R1.work/host

### Step 2: AI 编译

#### 依赖安装
- libbtbb: 已安装 (2020-12-R1)
- libusb-1.0: 从 cmd-pkgs 安装 (1.0.27)
- libpcap: 未安装（可选依赖）

#### CMake 配置
- 使用 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 解决版本兼容问题
- 使用 `-DENABLE_PYTHON=OFF` 禁用 Python 绑定

#### 编译结果
- ✅ 编译成功：libubertooth.so (70KB)
- ✅ 编译成功：11 个工具（ubertooth-rx, ubertooth-tx, etc.）
- ⏭️ 测试跳过：项目无 `make check` 目标

#### 安装产物
- lib/libubertooth.so
- include/ubertooth*.h
- bin/ubertooth-* (11个工具)
- share/man/man1/*.1, man7/*.7

### 关键问题及修复

#### 问题1: 库路径硬编码问题
- **错误**: 二进制文件硬编码相对路径 `../../libubertooth/src/libubertooth.so`
- **原因**: CMake 在同一源码树编译时使用相对路径链接
- **修复**: 创建软链接结构 `~/usr/libubertooth/src/libubertooth.so -> ~/usr/local/lib/libubertooth.so`
- **说明**: 这是 CMake 构建系统的设计问题，需要在打包时处理

#### 问题2: patchelf 权限限制
- **错误**: `patchelf: open: Operation not permitted`
- **原因**: SELinux/文件系统限制，无法修改已安装二进制
- **解决**: 使用软链接 workaround
---

## 预编译包制作（补充）

### 打包日期: 2026-06-11 15:25

### 问题诊断与修复
在首次编译完成后发现预编译包缺失，需补充制作。主要问题：
- 二进制文件硬编码相对路径 `../../libubertooth/src/libubertooth.so`
- libbtbb.so 使用绝对路径 `/storage/Users/currentUser/usr/local/lib/libbtbb.so`

### 修复步骤
1. **使用 patchelf 修复库依赖路径**
   - 在 staging 目录修复所有 11 个工具的库依赖
   - 替换相对路径为标准名称 `libubertooth.so`
   - 替换硬编码 libbtbb.so 路径为 `libbtbb.so`

2. **设置正确的 RPATH**
   - 所有工具设置 RUNPATH: `$ORIGIN/../lib`
   - libubertooth.so 设置 RUNPATH: `$ORIGIN`

3. **复制依赖库**
   - libusb-1.0.so.0.4.0 + 软链接
   - libbtbb.so

### 打包结果
- **ubertooth-2020-12-R1-ohos-aarch64.tar.gz**: 2457481 bytes (2.4MB)
- **ubertooth-2020-12-R1-ohos-aarch64-debug.tar.gz**: 1812778 bytes (1.8MB)
- **.packaged**: 打包标记文件

### 打包内容验证
- **bin/**: 11 个工具（ubertooth-rx, ubertooth-tx, etc.）+ 1 个 grepcidr
- **lib/**: libubertooth.so, libbtbb.so, libusb-1.0.so*
- **include/**: 5 个头文件
- **share/man/**: 11 个 man pages

### RPATH 验证
- RUNPATH: `[$ORIGIN/../lib:$ORIGIN/../lib/external]` ✅
- 库依赖：全部使用标准名称，无硬编码路径 ✅

### 用户安装说明
用户通过 cmd-pkgs 公共安装脚本安装后，库依赖将自动从 `$ORIGIN/../lib` 加载，无需手动创建软链接 workaround。
---

**编译结束**: 2026-06-11 15:27
**最终状态**: built
