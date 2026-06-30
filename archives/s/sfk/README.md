# Swiss File Knife (sfk)

Swiss File Knife 是一款多功能命令行工具，将众多常用 Unix 工具整合在一个二进制文件中，提供文件搜索、文本处理、二进制操作、网络工具等多种功能。

## 功能概述

- **文件系统**: list（列目录）、find（查找文件）、copy（复制）、sync（同步）、rename（重命名）、delete（删除）、md5（哈希校验）
- **文本处理**: filter（文本过滤）、find（文本搜索）、replace（替换）、sort（排序）、deblank（去空白）
- **二进制操作**: hexdump（十六进制查看）、partcopy（部分复制）、patch（补丁）
- **网络工具**: wget（HTTP下载）、ping（网络检测）、UDP/TCP 工具
- **压缩/解压**: zip/unzip 支持
- **其他工具**: calc（计算器）、space（磁盘空间）、filetime（文件时间）、calc（数值计算）

## OHOS 适配要点

### 1. fpos_t 在 musl 上的差异

OHOS/musl 的 `fpos_t` 是 `union _G_fpos64_t`，包含 `__lldata` (long long) 成员，而非 glibc 的 struct 带 `__pos` 成员。所有 `fpos_t.__pos` 的访问需添加 `#if defined(__OHOS__)` 分支，使用 `__lldata` 替代。

### 2. glibc 内部类型缺失

`__dev_t` 和 `__off_t` 是 glibc 专有类型，musl 未定义。需用 `#ifndef` 兜底定义映射为 `dev_t`/`off_t`。

### 3. config.status 在 HMDFS 上失败

Autoconf 2.65 的 config.status 在 HMDFS 文件系统上因 Permission denied 无法创建临时文件。需使用模式B手动编译（创建 config.h + 直接 clang++ 编译）。

### 4. SOL_IP 未定义

OHOS/musl 不定义 `SOL_IP`，需在多播代码中添加 `#define SOL_IP IPPROTO_IP`。

### 5. 平台检测

`__OHOS__` 是 clang 在 HarmonyOS 上的预定义宏，可用于 `#if defined(__OHOS__)` 条件编译。

## 依赖关系

无外部依赖。自包含 C++ 代码库。

## 参考资料

- 官网: http://stahlworks.com/dev/swiss-file-knife.html
- 源码: https://sourceforge.net/projects/swissfileknife/
- 许可证: BSD-2-Clause
