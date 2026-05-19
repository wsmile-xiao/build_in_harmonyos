# GMP 6.3.0 编译笔记

## 编译信息
- 编译日期: 2026-05-18
- 编译器: clang 15.0.4
- 构建类型: static library
- 平台: aarch64-unknown-linux-ohos

## 问题及解决方案

### 问题1: 平台识别失败
- **现象**: configfsf.guess 无法识别 HarmonyOS 平台
- **原因**: GMP 使用 configfsf.guess 和 configfsf.sub 进行平台识别，这些文件不支持 HarmonyOS
- **解决方案**: 替换为支持 HarmonyOS 的版本（复用 make 项目的已验证补丁）

### 问题2: 编译器测试程序无法运行
- **现象**: configure 脚本编译测试程序后无法运行（Permission denied）
- **原因**: HarmonyOS 要求 ELF 文件签名后才可执行，测试程序未签名
- **解决方案**: 
  1. 更新 clang-wrapper，使其在没有指定 -o 参数时也签名 a.out
  2. 在 configure 脚本中添加签名步骤

### 问题3: config.status 临时目录权限问题
- **现象**: config.status 无法在临时目录中创建 subs1.awk 文件（Permission denied）
- **原因**: HMDFS 文件系统不支持 umask 077 创建的目录
- **解决方案**: 修改 config.status，使用 TMPDIR 并移除 umask 077

### 问题4: 硬链接警告
- **现象**: libtool link 时无法创建硬链接（Operation not permitted）
- **原因**: HMDFS 不支持硬链接
- **解决方案**: libtool 自动使用 cp 替代 ln，不影响编译结果

## 验证结果
- libgmp.a: OK (1093896 bytes)
- gmp.h: OK (84255 bytes)
- pkg-config: OK (version 6.3.0)
- 功能测试: OK

## 编译命令记录
```bash
export PATH="$HOME/tmp/bin:$PATH"
export CC="clang-wrapper"
export CC_FOR_BUILD="clang-wrapper"
export DEFAULT_PREFIX="$HOME/usr/local"
export TMPDIR="$HOME/tmp"

./configure --prefix=$DEFAULT_PREFIX --disable-shared --enable-static ABI=64
make -j2
make install DESTDIR=$TEST_PREFIX
make install
```

## 注意事项
- 必须设置 TMPDIR 环境变量，避免在当前目录创建临时文件
- 必须设置 CC_FOR_BUILD 环境变量
- clang-wrapper 已更新以支持默认输出 a.out 的签名
