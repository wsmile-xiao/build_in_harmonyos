# disktype 9 适配笔记

## 编译环境
- 构建系统: makefile（无 configure 脚本，纯 Makefile 项目）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built
- 源码 SHA256: b6701254d88412bc5d2db869037745f65f94b900b59184157d072f35832c1111

## 编译步骤

disktype 是一个简单的纯 Makefile 项目，没有 configure 脚本，也没有 install/check 目标。

1. 下载源码 tarball 并解压
2. 手动编译：`make CC=clang CPPFLAGS="-D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DUSE_IOCTL_LINUX" CFLAGS="-Wall -fPIC -O2" -j1`
3. 手动安装到 staging（DESTDIR 模式，R20）：`cp disktype $TEST_PREFIX/$DEFAULT_PREFIX/bin/; cp disktype.1 ...`
4. 手动安装到 $DEFAULT_PREFIX：`cp disktype $DEFAULT_PREFIX/bin/; cp disktype.1 ...`

### 关键编译参数

由于 `uname` 返回 "HarmonyOS" 而非 "Linux"，Makefile 中的系统检测无法匹配 Linux 分支，因此需要手动添加 `-DUSE_IOCTL_LINUX` 到 CPPFLAGS，启用 Linux ioctl 支持（OpenHarmony 内核基于 Linux，ioctl 可正常使用）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CC=gcc` | Makefile 使用 gcc 作为默认编译器 | 通过 `make CC=clang` 命令行覆盖 |
| 2 | uname 返回 "HarmonyOS" 导致 USE_IOCTL_LINUX 未启用 | Makefile 用 `uname` 检测系统，只匹配 "Linux" | 手动添加 CPPFLAGS="-DUSE_IOCTL_LINUX" |
| 3 | 无 install 目标 | 项目设计为手动安装（README 明确说明） | 手动 cp 到 staging 和 $DEFAULT_PREFIX |
| 4 | 无 check 目标 | 项目无测试套件 | 跳过 make check，执行真实功能测试（10项全部通过） |
| 5 | G0 clean-verify CPPFLAGS 空格拆分 | configure_options 中 CPPFLAGS 多参数被 Python subprocess .split() 拆分，make 把 -D 误认为自身参数 | 创建 hints/clean-verify-hints.yaml 提供自定义 build_command 和 install_command |
| 6 | G4 manifest 缺少 build_system 顶层字段 | G4 检查顶层 `build_system:` 字段，manifest 中只有嵌套 `build.system` | 添加顶层 `build_system: makefile` |
| 7 | G1-G3 检查路径不匹配 DESTDIR 模式 | verify-build 查找 $TEST_PREFIX/bin，但 DESTDIR 模式下产物在 $TEST_PREFIX/$DEFAULT_PREFIX/bin | verify-build 使用 --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX |

## 源码修改

无源码修改。所有适配通过命令行参数覆盖完成（CC、CPPFLAGS、CFLAGS）。

编译过程中产生 6 个 warning（上游代码变量未使用：apple.c:109 version, unix.c:254 nsectors/ntracks/ncylinders/secpercyl/secperunit），均属于上游代码质量问题，不影响功能。

## 依赖版本

- clang 15.0.4
- 无外部库依赖（项目自包含）

## 真实功能测试结果

详细测试记录见 `reports/test-report.md`，以下是摘要：

| 测试项 | 结果 | 命令/输出摘要 |
|--------|------|---------------|
| 安全弹窗 (R7) | ✅ | disktype 直接执行，输出 Usage |
| 空文件检测 | ✅ | `Regular file, size 0 bytes` |
| 文本文件检测 | ✅ | `Regular file, size 18 bytes, Blank disk/medium` |
| tar 归档检测 | ✅ | `GNU tar archive` |
| tar.gz 双层检测 | ✅ | `gzip-compressed data → GNU tar archive`（递进分析） |
| 源码 tarball 检测 | ✅ | `gzip-compressed data → GNU tar archive` |
| ELF 二进制自检测 | ✅ | `Regular file, size 90.44 KiB (92608 bytes)` |
| 多文件参数 | ✅ | 逐一输出三个文件的检测结果 |
| ELF 格式验证 | ✅ | `ELF64 aarch64, dynamic (ld-musl)` |
| 预编译包内容 | ✅ | 包含 bin/disktype, man1/disktype.1, doc/* |

**总通过率**: 10/10 ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| disktype-9-ohos-aarch64.tar.gz | 167KB | 预编译包（已 strip + ELF 签名） |
| disktype-9-ohos-aarch64-debug.tar.gz | 35KB | debug 符号包 |

预编译包内容：bin/disktype, share/man/man1/disktype.1, share/doc/disktype/{README,LICENSE,HISTORY,TODO}

## G0-G4 质量门禁结果

| 门禁 | 结果 | 详情 |
|------|------|------|
| G0 干净构建 | ✅ PASS | hints 自定义命令，从原始 tarball 构建成功 |
| G1 二进制完整性 | ✅ PASS (✅1 ⚠️0 ❌0) | 1 个 ELF 二进制 |
| G2 功能可用性 | ✅ PASS (✅0 ⚠️1 ❌0) | ⚠️ disktype 不支持 --version（预期） |
| G3 可移植性 | ✅ PASS (✅0 ⚠️2 ❌0) | ⚠️ 无 RPATH（无共享库依赖），⚠️ staging 未签名（打包时已签） |
| G4 档案完整性 | ✅ PASS (✅0 ⚠️0 ❌0) | 所有必填文件完整 |

## 注意事项

- disktype 无 configure 脚本，属于纯 Makefile 项目
- 编译时必须手动指定 `CC=clang` 和 `CPPFLAGS="-DUSE_IOCTL_LINUX"`（因 uname=HarmonyOS）
- 项目无 install/check 目标，需手动安装
- 项目无任何外部依赖，自包含设计
- CPPFLAGS 多参数不能用 configure_options 列表传递（会被 .split() 拆分），必须通过 hints 文件
---

**编译结束**: 2026-07-15 15:41
**最终状态**: built
