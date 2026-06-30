# fwup 1.16.0 编译笔记

## 编译日期
2026-06-03

## 编译环境
- OpenHarmony 系统
- clang 编译器
- ARM64 架构

## 编译过程

### Step 1: 下载源码
- 从 GitHub 下载 fwup-1.16.0.tar.gz
- 解压到 ~/tmp/fwup-1.16.0-src

### Step 2: 配置环境
- 设置 PKG_CONFIG_PATH、LD_LIBRARY_PATH、PATH
- 设置 TMPDIR=~/tmp（避免 /tmp 只读问题）

### Step 3: configure
- 修复 HMDFS SELinux 问题：sed -i 's/umask 077/umask 022/g' configure
- 替换 config.guess/config.sub（使用 automake 提供的版本）
- configure 参数：--prefix=~/usr/local CFLAGS="-march=armv8-a+crypto -O2" CC=clang

### Step 4: 编译
- ARM AESCE 编译错误：添加 -march=armv8-a+crypto 编译选项
- reallocarray 链接错误：创建 reallocarray.c 实现

### Step 5: 链接
- 手动链接 fwup，添加 reallocarray.o 和 RPATH

### Step 6: 安装和打包
- 手动复制 fwup 到 staging 目录
- 创建预编译包：fwup-1.16.0-ohos-aarch64.tar.gz

## 遇到的问题及解决方案

### 问题 1: HMDFS SELinux umask 077
- **症状**: configure 无法创建临时文件
- **解决**: sed -i 's/umask 077/umask 022/g' configure

### 问题 2: config.guess 无法识别平台
- **症状**: "cannot guess build type"
- **解决**: 使用 automake 提供的 config.guess/config.sub

### 问题 3: ARM AESCE 编译错误
- **症状**: "assigning to 'uint8x16_t' from incompatible type 'int'"
- **解决**: 添加 -march=armv8-a+crypto 编译选项

### 问题 4: reallocarray 未定义
- **症状**: ld.lld: error: undefined reference due to --no-allow-shlib-undefined: reallocarray
- **解决**: 创建 reallocarray.c 实现

### 问题 5: liblzma 依赖缺失
- **症状**: ld.lld: error: undefined symbol: lzma_lzma_preset
- **解决**: 安装 lzma 预编译包

## 依赖说明
fwup 是动态链接的，运行时依赖：
- libconfuse.so（预编译包）
- libarchive.so（预编译包）
- lzma（libarchive 的依赖）

用户安装 fwup 预编译包后，需要先安装这些依赖：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libarchive 3.7.4
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libconfuse 3.3
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lzma 5.6.2
```

## 知识提取
- **E-fwup-hmdfs-umask**: HMDFS SELinux 导致 autotools configure 无法创建临时文件
  - 解决方案：修改 configure 脚本中的 umask 077 -> 022
- **E-fwup-arm-aesce**: ARM AES 扩展指令编译失败
  - 解决方案：添加 `-march=armv8-a+crypto` 编译选项
- **E-fwup-reallocarray**: reallocarray 函数未定义
  - 解决方案：手动创建 reallocarray.c 实现
