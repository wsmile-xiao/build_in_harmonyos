# git 2.49.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-25
- 编译器: clang (LLVM)
- 状态: partial（后修复为 published）

## 编译步骤
1. 下载 git-2.49.0.tar.gz 并解压
2. `./configure --prefix=$HOME/usr/local`
3. `make -j$(nproc)`
4. `make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | templates 目录缺失导致 git init 警告 | DESTDIR 模式未正确复制 templates | 从系统预装 git 复制 templates 内容 |
| 2 | safe.directory dubious ownership 错误 | git 2.35+ 安全特性 + HMDFS UID 映射 | 创建 etc/gitconfig 配置 safe.directory = * |

## 源码修改
无需源码修改

## 依赖版本
- zlib, openssl, curl, expat, gettext

## 验证结果
- git --version ✅
- git init ✅
- git clone ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| git-2.49.0-ohos-aarch64.tar.gz | 23.2MB | 主包（含 templates + etc/gitconfig） |

## 注意事项
- 预编译包需包含完整 `share/git-core/templates/` 目录
- 必须包含 `etc/gitconfig` 文件（含 safe.directory = *）
