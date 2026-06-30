# advancescan — ROM 扫描与差异比对工具

## 简介

advancescan 是一个命令行工具，用于扫描和验证 MAME（Multiple Arcade Machine Emulator）ROM 集合的完整性。它可以检测 ROM 文件是否正确、完整，并支持差异比对功能。

- **advscan**: 主扫描工具，检查 ROM 集合的完整性、正确性和一致性
- **advdiff**: 差异比对工具，比较两个 ROM 数据库之间的差异

## 版本

- **1.18** (当前已编译版本)

## 源码

- **URL**: https://github.com/amadvance/advancescan/releases/download/v1.18/advancescan-1.18.tar.gz
- **构建系统**: autotools

## 依赖

- zlib (压缩库)

## HarmonyOS 适配要点

1. **config.guess/config.sub**: 原版本为 2013 年，无法识别 HarmonyOS 平台，需替换为 GNU Config 2023 版并打 HarmonyOS 检测补丁（E007/E072）
2. **configure umask 077**: HMDFS 文件系统下 `umask 077` 创建的临时目录无法写入文件，需改为 `umask 022`
3. **autoreconf -fi**: 替换 config.guess/config.sub 后需重新生成 configure 脚本
4. **C++ 弃用警告**: 源码使用 `std::binary_function`（C++11 弃用），仅产生编译警告，不影响功能

## 编译配置

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 预编译包

- `advancescan-1.18-ohos-aarch64.tar.gz` (1098KB)
  - bin/advscan
  - bin/advdiff
  - share/man/man1/advscan.1
  - share/man/man1/advdiff.1

## 验证

```bash
advscan --version  # → advancescan v1.18
advdiff --version  # → advancescan v1.18
```
