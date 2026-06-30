# libexttextcat

## 简介

libexttextcat 是基于 N-Gram 的文本分类库，主要用于语言识别。它通过 N-gram 指纹对比技术，能够将输入文本自动识别为 178 种语言/方言。

## OHOS 适配

- autotools 构建（需 autoreconf -fvi 预生成 configure）
- 3.4.6 版本编译成功
- make check: 178 种语言识别测试全部 PASS
- API 功能测试全部通过（textcat_Init/Classify/Version/Done）
- createfp 工具可用
- 预编译包: libexttextcat-3.4.6-ohos-aarch64.tar.gz (919KB)

## 依赖

- 无编译依赖（仅需 libc）
- 构建时需 autoreconf（automake/autoconf/autoheader）

## 功能验证

### 库 API
```c
// 初始化（需在 fpdb.conf 所在目录下运行）
void *handle = textcat_Init("fpdb.conf");

// 语言识别
const char *result = textcat_Classify(handle, text, len);
// 英文 → [en--utf8], 中文 → [zh-CN-utf8], 法语 → [fr--utf8]

// 版本查询
const char *ver = textcat_Version();  // 返回 "3.4.6"

// 释放
textcat_Done(handle);
```

### 工具
```bash
# 创建指纹数据
echo "文本内容" | createfp
```

### 注意事项
- `textcat_Init` 需在包含 .lm 文件的目录下调用，或 fpdb.conf 中使用绝对路径
- 安装后包含 178 个语言模型文件 (.lm) 和 fpdb.conf 配置

## 补丁

- 0001-configure.patch: autoreconf 生成的 configure 脚本（原始 tarball 不含 configure）
- 0002-src-config.h.in.patch: autoheader 生成的 config.h.in（原始 tarball 不含此文件）

## 已知限制

- G0 干净构建验证: `/bin/sh` (toybox) 无法处理 autoconf 2.72 生成的 configure 脚本，需 bash 支持
- RUNPATH: 打包时需修正硬编码路径为通用安装路径

## 参考

- 主页: https://wiki.documentfoundation.org/DLP/Libexttextcat
- 源码: https://github.com/libexttextcat/libexttextcat/releases/tag/v3.4.6