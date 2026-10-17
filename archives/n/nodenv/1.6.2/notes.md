# nodenv 1.6.2 适配笔记

## 编译环境
- 构建系统: custom (纯 shell 薄本)
- 编译日期: 2026-06-05
- 编译器: 无需编译器（纯 shell 脚本）
- 状态: built

## 编译步骤

nodenv 是一个纯 shell 薄本项目，无需传统的 configure/make 流程。编译步骤如下：

1. 下载源码：从 GitHub 下载 nodenv-1.6.2.tar.gz
2. 解压源码：解压到 build 目录
3. 修改路径：在 libexec/nodenv 中将 /usr/local 替换为 ~/usr/local
4. 创建目录结构：bin, libexec, completions, nodenv.d, share/man/man1
5. 复制文件：将所有文件复制到 staging 目录
6. 验证安装：运行 nodenv --version 确认安装成功
7. 生成预编译包：打包为 tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用镜像源 ghproxy.net 下载 |
| 2 | build 脚本无法识别构建系统 | 无 configure/make | 手动编译（模式 B） |
| 3 | nodenv 运行失败 | libexec 路径未设置 | export PATH="$DEFAULT_PREFIX/libexec:$PATH" |

## 源码修改

### 0001-libexec-nodenv.patch

修改 libexec/nodenv 文件，将硬编码的 /usr/local 路径替换为实际安装路径：

```diff
- NODENV_HOOK_PATH="${NODENV_HOOK_PATH}:/usr/etc/nodenv.d:/usr/local/etc/nodenv.d:/etc/nodenv.d:/usr/lib/nodenv/hooks"
+ NODENV_HOOK_PATH="${NODENV_HOOK_PATH}:/usr/etc/nodenv.d:/storage/Users/currentUser/usr/local/etc/nodenv.d:/etc/nodenv.d:/usr/lib/nodenv/hooks"
```

## 依赖版本

nodenv 运行时需要：
- node-build（nodenv 插件，用于编译 Node.js 版本）
- bash（已预装）

## 验证结果

```bash
$ nodenv --version
nodenv 1.6.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nodenv-1.6.2-ohos-aarch64.tar.gz | 77K | 预编译包（纯 shell 薄本） |
| 0001-libexec-nodenv.patch | 1K | 路径前缀补丁 |

## 注意事项

1. nodenv 是纯 shell 薄本，不需要 ELF 签名
2. 运行前需要设置 PATH 环境变量包含 libexec 目录
3. 需要安装 node-build 插件才能编译 Node.js 版本
4. 不支持 G0 干净构建验证（无构建系统）

## 特殊处理说明

由于 nodenv 是纯 shell 薄本项目，跳过了以下标准流程：
- configure/make 编译流程
- G0 干净构建验证
- ELF 签名（无二进制文件）
- RPATH 设置（无动态库）
- Strip（无二进制文件）

安装方式：
- bin/nodenv 是入口脚本
- libexec/ 包含所有辅助脚本
- 运行时需要 PATH 包含 libexec 目录
---
**编译结束**: 2026-06-05 10:44
**最终状态**: built
---

**编译结束**: 2026-08-07 05:53
**最终状态**: built
