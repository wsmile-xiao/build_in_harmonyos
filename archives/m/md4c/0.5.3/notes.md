# md4c 0.5.3 适配笔记

## 编译环境
- 构建系统: cmake (上游原生, 未重写)
- 编译日期: 2026-08-24
- 编译器: clang/clang++
- 状态: built

## 软件简介

md4c 是一个用 C 实现的快速 Markdown 解析器, 采用 SAX-like 回调接口。
上游仓库: https://github.com/mity/md4c (MIT 许可证)。

核心 API 为 `md_parse(text, size, parser, userdata)`, 通过 `MD_PARSER`
结构体中的回调函数 (enter_block / leave_block / enter_span / leave_span /
text) 向调用方交付解析事件, 由调用方负责渲染输出。

上游同时提供 `md4c-html` 库 (HTML renderer), 内部调用 md4c parser 并
输出 HTML 字符串。

## 上游调查结果

| 项目 | 值 |
|------|-----|
| 仓库 | mity/md4c |
| tag | release-0.5.3 |
| commit | 472c417005c2c71b8617de4f7b8d6b30411d78f4 |
| 下载地址 | https://github.com/mity/md4c/archive/refs/tags/release-0.5.3.tar.gz |
| sha256 | 353c346f376b87c954a13f3415ede2d51264cc61dc5abcd38ff1d2aa0d059b9e |
| 许可证 | MIT |
| 语言 | C |
| 外部依赖 | 无 |

## 上游 CMake 构建分析

根 `CMakeLists.txt`:
- `option(BUILD_MD2HTML_EXECUTABLE ...)` — 控制 md2html 命令行工具构建 (默认 ON)
- `option(BUILD_SHARED_LIBS ...)` — 控制静态/动态库 (Linux 默认 ON)
- `add_subdirectory(src)` — 构建 md4c + md4c-html 库
- `add_subdirectory(md2html)` — 仅当 BUILD_MD2HTML_EXECUTABLE=ON 时构建可执行文件
- 无 examples / docs / 独立 ctest 测试子目录

`src/CMakeLists.txt`:
- `add_library(md4c md4c.c md4c.h)` — 核心 parser 库
- `add_library(md4c-html md4c-html.c md4c-html.h entity.c entity.h)` — HTML renderer
- `target_link_libraries(md4c-html PUBLIC md4c)` — md4c-html 依赖 md4c
- install EXPORT md4cConfig, NAMESPACE md4c:: — 导出 CMake 目标 `md4c::md4c` / `md4c::md4c-html`
- 安装 PUBLIC_HEADER: md4c.h, md4c-html.h

## 编译步骤

1. 源码下载: GitHub archive (release-0.5.3 tag, 固定 commit)
2. 使用上游原生 CMake 构建, 未修改任何源码或构建脚本
3. CMake 选项:
   - `BUILD_MD2HTML_EXECUTABLE=OFF` — 关闭命令行工具, 仅打包库
   - `BUILD_SHARED_LIBS=OFF` — 静态库 (R26: OHOS 交叉编译系统同名库须静态)
4. conan create 自动执行: cmake configure → cmake build → cmake install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tag 命名为 release-0.5.3 而非 v0.5.3 | md4c 采用 release- 前缀命名 | conandata.yml URL 使用 release-0.5.3 tag |
| 2 | 上游无 GitHub Release (仅 tag) | md4c 只打 tag 不建 Release | 用 archive/refs/tags/ 方式下载, sha256 实测 |

## 源码修改

无补丁。完全使用上游原生 CMake 构建, 未修改任何源码或 CMakeLists.txt。

## 依赖版本

无外部依赖, 纯 C 库。

## test_package 说明

test_package 链接 Conan package 产出的 `md4c::md4c` 目标 (通过 CMakeDeps
生成的 find_package 配置), 调用真实 `md_parse()` API 解析一个简单
Markdown 文档 (`# Title` + `**bold**`), 验证:

1. `md_parse()` 返回 0 (成功)
2. enter_block 回调触发 MD_BLOCK_DOC
3. enter_block 回调触发 MD_BLOCK_H, 且 heading level = 1
4. text 回调交付标题文本 "Title"
5. enter_span 回调触发 MD_SPAN_STRONG (加粗)
6. text 回调交付加粗内文本 "bold"

任一回调未按预期触发则测试退出非零。

## 注意事项

- 上游测试 (test/) 为 Python 脚本 (run-tests.py), 依赖预构建的 md2html
  可执行文件输出 HTML 做回归比对。本配方仅打包库、关闭 md2html 构建,
  故不纳入上游测试, 改用 test_package 直接验证 parser 回调 API。
- conanfile.py 声明两个 components: md4c (核心) 与 md4c-html (renderer),
  md4c-html.requires = ["md4c"] 保持上游依赖关系。

---

**编译结束**: 2026-08-24
**最终状态**: built
