# libxml2 2.15.3 编译笔记

uid: notes-v2

## 编译环境
- 构建系统: meson+ninja
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 目标平台: OpenHarmony aarch64, HongMeng Kernel 1.12.0
- 状态: built

### 对话 #1: libxml2 2.15.3 编译适配

**用户**: 编译 libxml2 2.15.3 for OpenHarmony

**助手**: 开始适配编译。首先下载源码并尝试 autotools 构建。

**发现**: autotools configure 在 HMDFS 上失败 — mktemp -d 创建的临时目录使用 umask 077，非 owner 用户无法写入，导致 config.status 执行失败。

**决策**: 改用 meson/ninja 构建。libxml2 2.15.x 官方推荐 meson 作为主构建系统，autotools 支持不完整（缺少 config.h.in）。

### 对话 #2: meson 构建配置

**用户**: 使用 meson 编译

**助手**: 配置 meson 构建：
- 修改 config.guess 添加 __OHOS__/HarmonyOS 系统识别
- 修改 config.sub 添加 linux-ohos* 三元组支持
- 修复 meson 预编译包的 shebang 和 PYTHONPATH

**构建命令**:
```
meson setup builddir --prefix=$DEFAULT_PREFIX --libdir=lib --buildtype=release -Ddefault_library=shared
ninja -j2
```

**结果**: 编译成功 ✅

### 对话 #3: 打包与验证

**用户**: 打包预编译包并验证

**助手**:
1. DESTDIR 安装到 staging 目录
2. 本地 install 到 DEFAULT_PREFIX
3. 使用 ohc-run.py package 打包（自动 ELF 签名、RPATH 设置、strip）
4. xmllint 本地安装版因未签名无法执行（报 "operation not permitted"）
5. 预编译包中的 xmllint 已签名，可正常执行

**验证**: xmllint --version 输出 `using libxml version 21503` ✅

## 编译步骤
1. 安装 meson 1.11.1 预编译包（修复 shebang 和 PYTHONPATH）
2. 修改 config.guess/config.sub 添加 linux-ohos 三元组支持
3. meson setup 构建（out-of-tree build）
4. ninja -j2 编译
5. DESTDIR 安装 + 本地 install
6. ohc-run.py package 打包

## 遇到的问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| autotools configure 失败 | HMDFS mktemp umask 077 权限问题 | 改用 meson+ninja 构建 |
| autotools 缺 config.h.in | libxml2 2.15.x meson 为主构建系统 | 使用 meson |
| config.sub 不识别 linux-ohos | 默认只支持 linux-gnu | 手动添加 linux-ohos* 三元组 |
| meson shebang 错误 | 指向不存在的 python3 路径 | sed 修复 + 创建 wrapper |
| xmllint 本地未签名不可执行 | OpenHarmony 要求 ELF 签名 | 使用预编译包中的签名版本 |

## 源码修改
- config.guess: 添加 HarmonyOS 系统识别（__OHOS__/HarmonyOS）
- config.sub: 添加 ohos-linux 三元组、linux-ohos* 内核处理、linux-ohos* OS 验证

## 知识积累 ✅

- ✅ E115: HMDFS mktemp 权限问题 + meson 构建替代方案
- ✅ E116: libxml2 2.15.x 使用 meson 作为主构建系统
- ✅ E117: meson 预编译包需要修复 shebang 和 PYTHONPATH
- ✅ E118: config.sub 需要添加 linux-ohos* 三元组支持

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxml2-2.15.3-ohos-aarch64.tar.gz | 4.6MB | 预编译包（ELF 已签名） |
| xmllint | ~2MB | XML 命令行工具 |
| xmlcatalog | ~2MB | XML 目录管理工具 |
| libxml2.so.16.1.3 | 1.4MB | 共享库 |

## 功能测试结果 ✅

14项功能测试全部通过（详见 test-report.md）：
- 版本确认、XML 解析、非法 XML 检测
- XPath 查询、属性过滤、C14N 规范化、XML 恢复
- UTF-8 编码、DTD 验证、网络/空白/格式化/输出功能

---

**编译结束**: 2026-06-02 16:25
**最终状态**: built
---

**编译结束**: 2026-06-02 16:37
**最终状态**: built
