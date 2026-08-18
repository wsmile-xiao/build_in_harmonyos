# dar 2.7.15 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang / clang++
- 状态: built (等待 CI 验证)

## 软件概述
DAR (Disk ARchive) 是一个全功能的磁盘归档和备份工具，支持：
- 全量/增量/差异备份
- gzip 压缩（通过 zlib）
- 分卷归档
- 文件排除/包含过滤
- 网络操作（通过 dar_slave/dar_xform）

## 产物
- **可执行文件**: dar, dar_xform, dar_slave, dar_manager, dar_cp, dar_split

## 编译步骤
1. 下载并解压 dar 2.7.15 源码
2. 应用 3 个补丁（config.guess/config.sub 平台识别 + configure umask 修复）
3. 运行 conan create 交叉编译

## 构建配置
- **静态链接**: 是（R26，系统工具需静态链接）
- **平台检测**: config.guess/config.sub 补丁添加 HarmonyOS 识别，AutotoolsToolchain 自动设置交叉编译三元组
- **mktemp wrapper**: HarmonyOS mktemp -d 创建目录权限异常，使用 wrapper 强制 fallback
- **umask 修复**: configure 脚本中 umask 077 改为 022

## 依赖处理
| 依赖 | 状态 | 处理方式 |
|------|------|----------|
| zlib | 已发布 (zlib/1.3.1) | Conan requires |
| bzip2 | 未在制品仓 | --disable-libbz2-linking |
| liblzo2 | 未在制品仓 | --disable-liblzo2-linking |
| liblzma (xz) | 未在制品仓 | --disable-libxz-linking |
| libzstd | 未在制品仓 | --disable-libzstd-linking |
| liblz4 | 未在制品仓 | --disable-liblz4-linking |
| libgcrypt | 未在制品仓 | --disable-libgcrypt-linking |
| libcurl | 未在制品仓 | --disable-libcurl-linking |
| gpgme | 未在制品仓 | --disable-gpgme-linking |
| libthreadar | 未在制品仓 | --disable-threadar |
| python | 不需要 | --disable-python-binding |
| upx | 不需要 | --disable-upx |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HarmonyOS 平台无法识别 | config.guess/config.sub 缺少 HarmonyOS 检测 | 补丁添加 aarch64:HarmonyOS 和 ohos-linux 识别 |
| 2 | configure 临时目录权限错误 | umask 077 在 HarmonyOS 上导致权限问题 | 补丁修改 umask 077 → 022 |
| 3 | mktemp -d 创建目录权限异常 | HarmonyOS MAC 策略影响 | mktemp wrapper 返回失败，强制 autoconf 使用 mkdir fallback |
| 4 | make check 无法在 CI 运行 | 交叉编译 aarch64 测试程序无法在 x86_64 CI worker 执行 | CI 跳过 make check，上游测试已在 OHOS aarch64 真机完整运行通过 |

## 验证结果

### 上游测试（真机验证）
- **运行环境**: OHOS aarch64 真机
- **测试命令**: `make check`
- **测试结果**: 4/4 通过（100%）
  - all_features（全功能集成测试）: PASS
  - bnonzero（bnonzero 测试）: PASS
  - padder（padder 测试）: PASS
  - uncompressible_file（不可压缩文件测试）: PASS

### test_package 测试（CI 验证）
- Test 1: `dar -V` — 验证 dar 二进制存在、可执行且输出包含 "dar" (test_package)
- Test 2: `dar -h` — 验证 dar 帮助信息输出包含 "dar" (test_package)
- Test 3: `dar_xform -V` — 验证 dar_xform 子工具存在、可执行且输出包含 "dar" (test_package)
- Test 4: `dar_manager` — 验证二进制存在且可执行 (test_package)
- Test 5: `dar_cp` — 验证二进制存在且可执行 (test_package)
- Test 6: `dar_slave` — 验证二进制存在且可执行 (test_package)
- Test 7: `dar_split` — 验证二进制存在且可执行 (test_package)

## 注意事项
- 首次运行会弹窗确认（鸿蒙安全机制）
- /tmp 只读，需设置 TMPDIR=$HOME/tmp
- 仅启用 gzip 压缩，其他压缩算法（bzip2/xz/zstd/lzo/lz4）已禁用
- 强加密（gcrypt/gpgme）已禁用
