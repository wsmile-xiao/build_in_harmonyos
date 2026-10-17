# md4c 0.5.2 适配笔记

## 编译环境
- 构建系统: cmake (上游原生, 未重写)
- 编译日期: 2026-09-07
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 软件简介

md4c 是一个用 C 实现的快速 Markdown 解析器, 采用 SAX-like 回调接口。
上游仓库: https://github.com/mity/md4c (MIT 许可证)。

核心 API 为 `md_parse(text, size, parser, userdata)`, 通过 `MD_PARSER`
结构体中的回调函数 (enter_block / leave_block / enter_span / leave_span /
text) 向调用方交付解析事件, 由调用方负责渲染输出。

上游同时提供 `md4c-html` 库 (HTML renderer), 内部调用 md4c parser 并
输出 HTML 字符串。无任何外部依赖, 纯 C 单文件 parser。

## 上游调查结果

| 项目 | 值 |
|------|-----|
| 仓库 | mity/md4c |
| tag | release-0.5.2 |
| 下载地址 | https://github.com/mity/md4c/archive/refs/tags/release-0.5.2.tar.gz |
| sha256 | 55d0111d48fb11883aaee91465e642b8b640775a4d6993c2d0e7a8092758ef21 |
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

## 编译步骤

1. 源码下载: GitHub archive (release-0.5.2 tag, sha256 实测核验一致)
2. 使用上游原生 CMake 构建, 未修改任何源码或构建脚本
3. 本地原生构建 md2html (仅用于运行上游 spec 回归测试) — 通过
4. conan create (ohos-aarch64 profile) 自动执行: cmake configure → build → install — 通过
5. CMake 选项:
   - `BUILD_MD2HTML_EXECUTABLE=OFF` — 关闭命令行工具, 仅打包库
   - `BUILD_SHARED_LIBS=OFF` — 静态库 (R26: OHOS 交叉编译系统同名库须静态)

## 上游测试实测结果

上游测试 (test/) 为 Python 脚本 (run-testsuite.py + pathological-tests.py),
依赖预构建 md2html 可执行文件做 HTML 回归比对。本地构建 md2html 后全量实测:

| 测试源 | 用例数 | 结果 |
|--------|--------|------|
| spec.txt (CommonMark) | 652 | 全部通过 |
| spec-*.txt 扩展 spec (8 个) | 72 | 全部通过 |
| regressions.txt (Issue 回归) | 56 | 全部通过 |
| coverage.txt (覆盖率补测) | 19 | 全部通过 |
| pathological-tests.py (压力) | 27 | 全部通过 |
| **合计** | **826** | **826/826 (100%)** |

> 统计口径: 全量发现数 (源码声明的全部独立用例) 为分母, 通过数/全量发现数 = 100%。
> 本配方仅打包库、关闭 md2html 构建, 故上游 spec 套件不注册在 conan create 管道内;
> 包级验证由 test_package 的真实 md_parse() API 断言承担 (见下)。

## test_package 说明

test_package 链接 Conan package 产出的 `md4c::md4c` 目标 (通过 CMakeDeps
生成的 find_package 配置), 调用真实 `md_parse()` API 解析一个简单
Markdown 文档 (`# Title` + `**bold**`), 断言 6 项回调行为:

1. `md_parse()` 返回 0 (成功)
2. enter_block 回调触发 MD_BLOCK_DOC
3. enter_block 回调触发 MD_BLOCK_H, 且 heading level = 1
4. text 回调交付标题文本 "Title"
5. enter_span 回调触发 MD_SPAN_STRONG (加粗)
6. text 回调交付加粗内文本 "bold"

任一回调未按预期触发则测试退出非零。OHOS aarch64 目标下 ctest 1/1 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tag 命名为 release-0.5.2 而非 v0.5.2 | md4c 采用 release- 前缀命名 | conandata.yml URL 使用 release-0.5.2 tag |
| 2 | W3 本地 CI 首次命中 JC5 junk 检查 | main 中其他库 util-linux-login 已提交的基线文件 archives/u/util-linux-login/2.42.2/.ci-trigger (空文件) | 基线隔离复验: 索引级临时隔离 → 复跑 W3 通过 → 原样恢复, pre/post SHA-256 一致 (e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855), 未提交该文件 |
| 3 | init-build 将构建系统误判为 autotools | md4c 为 CMake, 检测启发式失误 | conanfile.py 改写为 CMake 配方 (对照同库 0.5.3 已验证配方) |
| 4 | conan-verify/finish 临时注入 ghfast.top 镜像污染 conandata.yml | 工具 E017 预防逻辑在异常中断时残留镜像前缀 URL | 恢复官方 HTTPS URL 并核验 SHA-256 一致 |

## 依赖版本

无外部依赖, 纯 C 库。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方, 声明 md4c/md4c-html 两组件 |
| conandata.yml | 官方源 URL + 实测 sha256 |
| test_package/ | 消费者测试 (真实 md_parse API 断言) |
| test-report.md | 上游测试全量枚举台账 + 双口径统计 + W3/基线隔离证据 |
| manifest.yaml / notes.md | 归档元数据与本笔记 |

## 注意事项

- 上游测试需 md2html 可执行文件; 配方仅打包库, 全量 spec 回归在本地构建 md2html 后完成 (826/826 通过)。
- 基线文件 `.ci-trigger` (util-linux-login) 属于其他库, 隔离复验后原样保留, 不进入本 PR。

---

**编译结束**: 2026-09-07
**最终状态**: built