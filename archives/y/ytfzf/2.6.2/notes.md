# ytfzf 2.6.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 shell 脚本工具）
- 编译日期: 2026-06-02
- 编译器: clang/clang++（实际未使用，ytfzf 为纯 shell 脚本）
- 状态: built

## 编译步骤

ytfzf 是纯 POSIX shell 脚本工具，无需 configure/make 编译步骤，直接使用 make install 安装：

```bash
cd $BUILD_SRC_DIR
source $BUILD_CONTEXT_FILE

# DESTDIR 模式（R20）安装三个目标
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make doc PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make addons PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

- install 目标：用 sed 自动替换脚本中的 YTFZF_SYSTEM_ADDON_DIR 路径，安装到 DESTDIR
- doc 目标：安装 man 页面、配置示例和 LICENSE
- addons 目标：安装所有 addons（interfaces, scrapers, sort-names, thumbnail-viewers, url-handlers, extensions）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ytfzf --version 报错缺少 jq | ytfzf 运行时依赖 jq，未安装 | 记录为运行时依赖，不影响编译/打包 |
| 2 | G4 门禁报 "manifest 缺少 build_system" | 版本级 manifest 缺少 build_system 顶层字段 | 补充 build_system: makefile |
| 3 | G4 门禁报 "无二进制文件" | ytfzf 是 shell 脚本，不是 ELF 二进制 | 记录为平台特性，shell 脚本工具无 ELF 产物 |

## 源码修改

无补丁。源码无需修改：
- ytfzf 使用 `${TMPDIR:-/tmp}` 正确适配 HarmonyOS TMPDIR（无需 E002 补丁）
- Makefile 的 install 步骤自动处理 YTFZF_SYSTEM_ADDON_DIR 路径替换
- DESTDIR 模式天然支持 R20

## 依赖版本

运行时依赖（未安装，不影响编译）：
- jq（未安装）
- curl（系统自带）
- fzf（未安装）

## 验证结果

```bash
# Staging 安装产物检查
$ find $TEST_PREFIX/$DEFAULT_PREFIX -type f | wc -l
43 文件

# 关键文件检查
$ ls $TEST_PREFIX/$DEFAULT_PREFIX/bin/ytfzf  # ✅ 存在
$ ls $TEST_PREFIX/$DEFAULT_PREFIX/share/ytfzf/addons/  # ✅ 6 个 addon 目录

# ytfzf --version 需要 jq 运行时依赖
$ $TEST_PREFIX/$DEFAULT_PREFIX/bin/ytfzf --version
[ERROR]: You are missing the following required dependencies, jq
```

## 交付物

| 文件 | 说明 |
|------|------|
| ytfzf-2.6.2-ohos-aarch64.tar.gz | 预编译包（含 ytfzf 脚本 + addons + doc） |
| ytfzf-2.6.2-ohos-aarch64-debug.tar.gz | 调试包 |

## 注意事项

- ytfzf 是纯 shell 脚本，非 ELF 二进制，因此 G1/G2/G3 ELF 签名/strip/RPATH 检查不适用
- 运行时必须先安装 jq 依赖才能使用 ytfzf
- YTFZF_SYSTEM_ADDON_DIR 在 install 步骤被 Makefile 自动替换为正确 PREFIX 路径
---

**编译结束**: 2026-06-02 10:42
**最终状态**: built
