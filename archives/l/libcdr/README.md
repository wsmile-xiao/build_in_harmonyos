# libcdr

libcdr 是一个用于解析和导入 CorelDRAW 文档（.cdr 和 .cmx 格式）的 C++ 库，由 LibreOffice 项目维护。它可以将 CorelDRAW 文档转换为 SVG、纯文本等格式，主要被 LibreOffice 用于导入 CorelDRAW 矢量图形文件。

## 功能概述

- **CDR 格式解析**：支持 CorelDRAW 3.0 至 X7（版本 300-1700）的 .cdr 文件
- **CMX 格式解析**：支持 Corel Clipart Exchange（.cmx）文件
- **Waldo 格式**：支持早期 CorelDRAW 的 Waldo 格式（版本 200）
- **格式转换工具**：
  - `cdr2raw` — 输出 RVNG 原始格式（调试用）
  - `cdr2xhtml` — 转换 CorelDRAW 文档为 SVG
  - `cdr2text` — 提取 CorelDRAW 文档中的文本
  - `cmx2raw` / `cmx2xhtml` / `cmx2text` — CMX 格式对应的转换工具
- **C++ API**：提供 `CDRDocument::isSupported()` 和 `CDRDocument::parse()` 静态方法

## OHOS 适配

### 适配要点

1. **平台检测**：config.guess/config.sub 不含 HarmonyOS 检测分支，需打补丁添加 `linux-ohos` 支持
2. **HMDFS 权限**：configure 脚本中 `umask 077` 在 HMDFS 文件系统上创建的目录权限为 0700，由于 UID 映射差异导致当前进程不可写，需改为 `umask 022`
3. **ICU 兼容性**：ICU 77+ 移除了 `TRUE`/`FALSE` 宏定义，源码中直接使用这些宏的代码需要替换为 C++ `true`/`false`
4. **Boost 守卫**：Boost 1.84.0 的 `sp_thread_sleep.hpp` 使用 `pthread_setcancelstate`（musl 不支持），需在系统级头文件中添加 `!defined(__OHOS__)` 守卫
5. **编译警告**：clang 的 `-Wdeprecated-copy-with-user-provided-copy` 警告被 `-Werror` 升级为错误，使用 `--disable-werror` 解决

### 已知问题

- G0 干净构建验证因 Python subprocess shell 引号问题在鸿蒙上 FAIL，属平台限制，非实际编译失败
- Boost `sp_thread_sleep.hpp` 的修改为系统级修复，不属于 libcdr 源码补丁范围

## 依赖关系

### 编译依赖

| 依赖 | 用途 |
|------|------|
| librevenge | 文档解析框架（RVNG 接口） |
| lcms2 | 色彩管理系统 |
| zlib | 压缩解压支持 |
| icu4c | Unicode 国际化支持 |
| boost | 头文件库（spirit 等） |
| cppunit | 单元测试框架（仅测试用） |

### 运行时依赖

- librevenge-0.0.so.0
- liblcms2.so.2
- libc++_shared.so
- libc.so

## 参考资料

- 项目主页：https://wiki.documentfoundation.org/DLP/Libcdr
- 源码仓库：https://gitlab.freedesktop.org/libreoffice/libcdr
- Bug 报告：https://bugs.documentfoundation.org/
- 许可证：Mozilla Public License 2.0 (MPL-2.0)
