# dar 2.7.15+dup2 适配笔记

## 任务背景（dup2 重复任务）

- **平台任务**: contrib-2095（开源鸿蒙PC专项积分赛，dup2 重复任务，用户 j669539 已认领）
- **版本策略（R37）**: 制品仓已存在 `dar/2.7.15`（rev 8541f8bf）与 `dar/2.7.15.1`（rev d9e12852），
  `conan download --only-recipe` 实测确认。cnb.cool 制品仓不支持同版本多 recipe revision 并存，
  重复任务必须递增适配后缀 → **2.7.15+dup2**（R37：上游版本 + 适配修复后缀 N 递增）。
- **源码**: 同 2.7.15 官方 tarball（`dar-2.7.15.tar.gz`，sha256 `fac56b59...`），URL 与 sha256 均不变。
- **分支名**: `feat/dar-2.7.15+dup2`（CI L0n 硬性要求分支名与归档版本精确匹配；
  平台 taskBranch `feat/dar-2.7.15-dup2` 带后缀会被 L0n 拦截，故以 CI 合规分支名为准，
  差异已在 PR 描述中说明）。

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-03
- 编译器: clang / clang++（OHOS aarch64 原生环境）
- 状态: built（W3 conan create 本地验证通过）

## 软件概述
DAR (Disk ARchive) 是一个全功能的磁盘归档和备份工具，支持：
- 全量/增量/差异备份
- gzip 压缩（通过 zlib）
- 分卷归档
- 文件排除/包含过滤
- 网络操作（通过 dar_slave/dar_xform）

## 产物
- **可执行文件**: dar, dar_xform, dar_slave, dar_manager, dar_cp, dar_split

## 与 2.7.15.1 的差异清单

| 项 | 2.7.15.1 | 2.7.15+dup2（本版本） |
|----|----------|--------------------|
| version（conanfile.py / manifest.yaml） | 2.7.15.1 | 2.7.15+dup2 |
| 源码 URL / sha256 | 同（dar-2.7.15.tar.gz） | 同（完全不变） |
| 补丁集（3 个 portability 补丁） | 0001/0002/0003 | 完全复用，逐字节相同 |
| configure 选项（14 个 --disable-*） | 同 | 完全相同 |
| 依赖（zlib/1.3.1） | 同 | 完全相同 |
| **zlib 链接（generate()）** | **无 AutotoolsDeps → zlib 未链接，`dar -V` 显示 gzip NO** | **新增 `AutotoolsDeps` 注入 -I/-L/-l → zlib 正确链接，gzip YES** |
| test_package（test_dar.sh 7 项测试） | 同 | 完全复用 |
| mktemp wrapper / -static 链接 | 同 | 完全相同 |
| 版本递增原因 | 制品仓已有 2.7.15 | 制品仓已有 2.7.15 与 2.7.15.1（dup2） |
| manifest build_date | 2026-07-17 | 2026-09-03 |

**核心适配修复（R37 版本递增的实质内容）**：2.7.15.1 的配方缺 `AutotoolsDeps` 生成器，
configure 探测 `deflate in -lz` 时 `ld.lld: unable to find library -lz` 失败，zlib 被静默
编译出 dar（`dar -V` 显示 `gzip compression (libz): NO`，制品仓 2.7.15.1 二进制实测确认）。
2.7.15+dup2 在 `generate()` 中添加 `AutotoolsDeps` 后 zlib 正确链接，gzip 压缩功能恢复
（`dar -V` 显示 `gzip compression (libz): YES`，压缩归档往返实测通过）。

## 编译步骤
1. 下载并解压 dar 2.7.15 源码（同 tarball）
2. 应用 3 个补丁（config.guess/config.sub 平台识别 + configure umask 修复）
3. 运行 conan create 交叉编译（zlib/1.3.1 为唯一依赖）

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
| 4 | make check 无法在 CI 运行 | 交叉编译 aarch64 测试程序无法在 x86_64 CI worker 执行 | CI 跳过 make check（no_official_test 白名单），上游测试在 OHOS aarch64 真机运行 |
| 5 | R37 版本冲突 | 制品仓已有 dar/2.7.15 与 dar/2.7.15.1 | 版本号递增至 2.7.15+dup2（源码/补丁/配置完全复用 2.7.15.1 先例） |
| 6 | zlib 未链接（2.7.15.1 遗留缺陷） | 配方缺 AutotoolsDeps，configure 探测 -lz 失败后静默禁用 gzip | generate() 添加 AutotoolsDeps 注入 -I/-L/-l，zlib 正确链接（gzip YES） |

## 验证结果

### conan create（W3 本地验证）
- `conan create . --user=ohpcd --channel=stable -pr:h/-pr:b=ohos-aarch64 --build=missing`
- 构建成功，0 error；`checking for deflate in -lz... yes`
- test_package 7 项测试全部 PASS（dar -V / dar -h / dar_xform / dar_manager / dar_cp / dar_slave / dar_split）

### 上游测试与功能测试（OHOS aarch64 原生环境实测）
- **运行环境**: OHOS aarch64 原生环境（本机），构建产物二进制 + LD_LIBRARY_PATH 指向 OHOS SDK libc++
- **测试矩阵（7/7 通过，100%）**:
  - T1 无压缩归档往返（-c/-x + diff）: PASS
  - T2 gzip 压缩归档往返（-z6，zlib 修复核心验证）: PASS
  - T3 归档完整性测试（-t）: PASS
  - T4 归档与源差异对比（-d）: PASS
  - T5 归档内容列表（-l）: PASS
  - T6 dar_xform 分卷（-s 1K）+ 分卷恢复往返: PASS
  - T7 上游 check 程序 bnonzero + padder: PASS
- **上游 make check 说明（与 2.7.15.1 先例处理方式一致）**:
  - 上游 `make check` 套件（check-local → my_env → my_makefile → main.sh 数千组合）前置要求
    root 权限、GPG 密钥（DAR_KEY）、SFTP/FTP 仓库（DAR_SFTP_REPO/DAR_FTP_REPO）及全部压缩
    算法特性（all_features 程序校验 gzip+bzip2+lzo+xz+zstd+lz4 全部可用）——OHOS 环境不可满足，
    先例（2.7.15.1）同样未执行完整套件并在 notes 记录环境类原因。
  - 上游 check 中可独立运行的单元（bnonzero/padder）与 dar 工具家族功能级往返测试已实测通过
    （上述 T1-T7）；all_features 因 bzip2/lzo/xz/zstd/lz4 依赖被 --disable（制品仓虽有
    bzip2/1.0.8 等，但保持与 2.7.15.1 先例的 14 项 --disable 配置一致，避免 dup2 任务变更面
    扩大）而无法全过，属配置类限制，非本版本回归。
  - CI 交叉编译环境加入 no_official_test 白名单跳过（同先例）。

### gzip 支持对比（2.7.15.1 → 2.7.15+dup2）
| 版本 | dar -V 显示 | 压缩归档实测 |
|------|------------|--------------|
| 2.7.15.1（制品仓二进制实测） | gzip compression (libz): NO | -z1 报 "feature disabled at compilation time" |
| 2.7.15+dup2（本地构建实测） | gzip compression (libz): YES | -z6 压缩归档创建/恢复往返 PASS |

## 注意事项
- 首次运行会弹窗确认（鸿蒙安全机制）
- /tmp 只读，需设置 TMPDIR=$HOME/tmp
- 仅启用 gzip 压缩，其他压缩算法（bzip2/xz/zstd/lzo/lz4）已禁用
- 强加密（gcrypt/gpgme）已禁用
---

**编译结束**: 2026-09-03 01:39
**最终状态**: published
