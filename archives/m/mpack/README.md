# mpack

## 软件简介
mpack 是一个 MIME 邮件打包和解包工具集，用于处理电子邮件附件的编码和解码。

## 基本信息
- **名称**: mpack
- **版本**: 1.6
- **许可证**: BSD-3-Clause
- **构建系统**: autotools
- **源码地址**: https://ftp.gwdg.de/pub/misc/mpack/mpack-1.6.tar.gz

## 功能描述
mpack 工具集包含两个主要程序：

### mpack
- 功能：将文件打包成 MIME 格式的电子邮件附件
- 支持：Base64、Quoted-Printable 等编码方式
- 用途：发送邮件附件、创建 MIME 格式文件

### munpack
- 功能：解析 MIME 格式文件并提取附件
- 支持：自动识别编码格式
- 用途：解码邮件附件、提取 MIME 内容

## 使用示例

### 打包文件
```bash
# 创建 MIME 格式文件
mpack -s "邮件主题" -o output.mime input.txt

# 发送邮件（需要邮件服务器）
mpack -s "邮件主题" file.txt user@example.com
```

### 解包文件
```bash
# 从 MIME 文件提取附件
munpack -f output.mime

# 从标准输入解包
munpack < email.mime
```

## 依赖关系
- **无外部依赖**
- 仅需要标准 C 库

## 编译信息

### 编译环境
- 构建系统: autotools
- 编译器: clang
- 平台: OpenHarmony aarch64

### 编译选项
```bash
./configure --prefix=$DEFAULT_PREFIX
make
make install
```

### 补丁信息
- 0001-fix-return-value.patch: 修复 uudecode.c 返回值问题

### 已知问题
- 旧式 C 代码产生大量编译警告（非致命）
- 无单元测试套件

## 安装验证

### 版本检查
```bash
mpack  # 显示版本 1.6
munpack  # 显示版本 1.6
```

### 功能测试
- ✅ MIME 打包功能正常
- ✅ MIME 解包功能正常
- ✅ 错误处理机制完善

## 文档资源
- man/mpack.1 - mpack 使用手册
- man/munpack.1 - munpack 使用手册

## 版本历史
- 1.6 (2003-07-22): 当前稳定版本
- 早期版本支持 Mac 和 Unix 平台

## 相关链接
- 源码仓库: https://ftp.gwdg.de/pub/misc/mpack/
- Debian 包: https://packages.debian.org/mpack