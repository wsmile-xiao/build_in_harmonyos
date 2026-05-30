# GNU grep 3.11 编译笔记

## 编译日期
2026-05-18

## 软件信息
- 名称: GNU grep
- 版本: 3.11
- 构建系统: autotools
- 依赖: pcre2 10.47 (系统预装)

## 编译过程

### 1. 源码下载
从 GNU 官方镜像下载源码包 grep-3.11.tar.xz (1.6M)

### 2. 平台识别问题
configure 脚本无法识别鸿蒙平台，错误信息：
```
./build-aux/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

解决方案：从已编译成功的 make-4.4.1 项目复制更新的 config.guess 和 config.sub 文件，识别为 `aarch64-unknown-linux-ohos`

### 3. 临时目录权限问题
configure 运行成功但 config.status 创建临时文件失败：
```
./config.status[2330]: can't create ./confXXXXXX/subs1.awk: Permission denied
```

原因：HMDFS 文件系统限制，无法在当前目录创建临时目录

解决方案：修改 config.status 脚本，将 `./confXXXXXX` 替换为 `/storage/Users/currentUser/tmp/confXXXXXX`

### 4. 编译选项
```bash
./configure --prefix=$DEFAULT_PREFIX --enable-perl-regexp
make -j2
```

### 5. 功能验证
- grep --version 输出正确，显示 PCRE2 10.47 支持
- 基本搜索功能正常
- PCRE2 正则表达式 (-P 选项) 功能正常

## 验证结果
```
grep (GNU grep) 3.11
grep -P uses PCRE2 10.47 2025-10-21
```

## 预编译包
- 路径: archives/g/grep/3.11/packaging/grep-3.11-ohos-aarch64.tar.gz
- 内容: grep, egrep, fgrep

## 遇到的问题及解决方案
1. **平台识别失败** - 更新 config.guess/config.sub
2. **临时目录权限** - 修改 config.status 使用 TMPDIR
3. **PCRE2 依赖** - 使用系统预装的 pcre2 10.47

## 编译状态
✅ 成功完成编译、安装和功能验证