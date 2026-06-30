# espeak-ng 1.51 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**: 已有 tarball `espeak-ng-1.51.tar.gz` (14M)
2. **解压**: 解压为原始目录和工作目录
3. **生成构建文件**: 运行 `autogen.sh --foreign` 生成 configure
4. **配置**: `bash ./configure --prefix=$DEFAULT_PREFIX` (需要修改 config.status)
5. **编译**: `make -j1` (成功)
6. **安装**: `make install DESTDIR=$TEST_PREFIX` (成功)
7. **验证**: `espeak-ng --version` 输出 "eSpeak NG text-to-speech: 1.51"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 失败 | automake 需要 GNU 标准文件 (NEWS, ChangeLog.md) | 使用 `--foreign` 选项绕过 GNU 标准 |
| 2 | HMDFS 临时目录权限 | mktemp 创建的目录权限不可修改 (umask 077) | 修改 config.status，使用绝对路径 + umask 022 |
| 3 | CHANGELOG.md 符号链接失效 | HMDFS 软链接不稳定 | 复制实际文件而非符号链接 |
| 4 | toybox sh 不兼容 | toybox sh 不完全兼容 config.status | 使用 bash 运行 configure |

## 源码修改

**无补丁**：本次编译未修改任何源文件。

### 文件说明

- **config.guess / config.sub**: autogen.sh 自动生成，已支持 OpenHarmony（无需修改）
- **config.status**: configure 生成的文件，需修改 umask（记录在知识库，不作为补丁）
- **字典数据**: 编译时自动生成，不需要补丁

## 依赖版本

- clang: 18.1.8
- automake: 1.16.5
- autoconf: 2.71
- libtool: 2.4.7
- make: GNU Make 4.4.1

## 验证结果

```bash
$ espeak-ng --version
eSpeak NG text-to-speech: 1.51  Data at: /storage/Users/currentUser/usr/local/share/espeak-ng-data

$ ls -lh ~/usr/local/bin/espeak*
lrwxrwxrwx espeak -> espeak-ng
-rwxr-x--- espeak-ng (54K)
lrwxrwxrwx speak -> speak-ng
-rwxr-x--- speak-ng (1.2M)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| espeak-ng-1.51-ohos-aarch64.tar.gz | 17M | 预编译包（已存在）|
| espeak-ng-1.51.tar.gz | 14M | 源码包 |

## 注意事项

1. **HMDFS 文件系统限制**: mktemp 创建的目录权限不可修改，需修改 config.status
2. **无补丁原则**: 本次编译未修改任何源文件，符合 R2/R6 规则
3. **知识沉淀**: config.status umask 问题已记录为平台真理（L1 知识）

---
**编译结束**: 2026-05-27 21:14
**最终状态**: built