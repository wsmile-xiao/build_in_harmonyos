# scheme48

## 软件简介

Scheme48 是一个 Scheme 编程语言的实现，基于字节码虚拟机（byte-code interpreter）。它由 MIT 的 Richard Kelsey 和 Jonathan Rees 设计实现，包含一个完整的字节码编译器、运行时系统和丰富的标准库。

### 核心特性

- **字节码虚拟机**：使用 BIBOP（Big Bag of Pages）内存管理策略
- **完整 R5RS 支持**：包含 hygienic 宏系统、尾调用优化、第一类续延
- **模块系统**：强大的结构和模块机制
- **POSIX 接口**：通过动态加载库提供 POSIX 系统调用
- **FFI 支持**：外部函数接口，可加载 C 扩展
- **R6RS 部分支持**：包括 IEEE 字节向量等
- **CML 风格并发**：基于消息传递的并发原语

## 版本列表

| 版本 | 状态 | 编译日期 | 补丁数 | 预编译包 |
|------|------|----------|--------|----------|
| 1.9.3 | published | 2026-06-18 | 3 | ✅ scheme48-1.9.3-ohos-aarch64.tar.gz |

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools |
| 语言 | C |
| 编译器 | clang 15.0.4 |
| 外部依赖 | 无 |
| 源码 URL | https://s48.org/1.9.3/scheme48-1.9.3.tgz |

## 鸿蒙适配说明

scheme48 在鸿蒙平台编译时需要以下适配：

1. **config.guess 更新**：添加 HarmonyOS 平台识别
2. **umask 修复**：config.status 的 `umask 077` 与 HMDFS 不兼容，改为 `umask 022`
3. **/tmp 路径修正**：Makefile 中硬编码的 `/tmp/` 替换为 `$TMPDIR/`
4. **ELF 签名**：所有可执行文件和 .so 共享库需在运行前签名

详见 [1.9.3 版本归档](1.9.3/notes.md)。
