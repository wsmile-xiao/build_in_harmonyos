# picohttpparser

极简 HTTP 请求/响应解析库，单文件 C 实现，零外部依赖。

Upstream: https://github.com/h2o/picohttpparser

## 版本（升级关系）

| 版本 | 状态 | 说明 |
|------|------|------|
| **1.4** | **built（当前版本，supersedes 1.2）** | 升级目标版本：`build()` 内集成并实测上游 TAP 测试套件（8 个顶层条目 / 299 条断言全部通过），`test_package` 35 项消费者 API 断言 |
| 1.2 | archived（已被 1.4 取代） | 早期模板产物：`manifest.yaml`/`notes.md` 含未替换占位符、未集成上游测试；制品仓保留 `picohttpparser/1.2` 配方供历史消费者引用 |

### 上游 1.2 → 1.4 差异（实测）

| 项 | 结论 |
|----|------|
| 公共 API | **完全不变**（`phr_parse_request` / `phr_parse_response` / `phr_parse_headers` / `phr_decode_chunked` 签名一致） |
| 头文件 | 仅版本宏更新：`PICOHTTPPARSER_VERSION` `"1.2"`→`"1.4"`、`PICOHTTPPARSER_VERSION_MINOR` `2`→`4` |
| 实现文件 | 10 行改动：① `likely`/`unlikely` 宏加 `#ifndef` 守卫（避免与外部已定义同名宏冲突）；② chunked 解码开销阈值 `100 * 1024` 写法归一为 `102400`（等价常量） |
| 上游测试 | `test.c` 逐字节未变（故断言数仍为 299，1.2/1.4 可横向对比） |

> 结论：这是**API/ABI 兼容的小版本升级**，对下游消费者无迁移成本；本次 PR 的主要价值在于把配方从早期模板产物升级到现行规范（真实上游测试 + 完整 test_package + 补建软件级元数据）。

## OHOS 适配要点

- **无构建系统**：上游 Makefile 只承载测试目标（`test-bin` + `prove -v`），库本体由配方直接用
  Conan conf 提供的 `clang` / `llvm-ar` 编译单一翻译单元（R33：不依赖裸 shell 变量）。
- **上游测试依赖子模块**：`picotest` 是 `.gitmodules` 声明的测试框架子模块，GitHub 源码 tarball
  不含其内容（`picotest/` 为空目录）。`conandata.yml` 因此包含第二个 source，从
  `h2o/picotest` 的钉定 commit（`70b9797596d81896cba49e5918fd5b1edf57269b`）获取，保证可复现。
- **上游测试在 build() 内执行**：按上游 Makefile 的方式编译 `test-bin`
  （`-Wall -fsanitize=address,undefined`）后直接运行；`picotest` 的 `done_testing()`
  以失败数作为进程退出码，与上游 `prove` 判定等价。
- **运行时包装**：OHOS 上 `/system/bin/sh` 可能无法直接 exec ELF，测试二进制经 bash 包装执行。
- **链接形态**：本库无系统同名库（不存在 `/lib/libpicohttpparser.so`），不触发 R26 静态约束；
  沿用 1.2 的纯静态打包形态（`libpicohttpparser.a`），保持下游 lib 名解析一致。

## 目录

```
picohttpparser/
├── manifest.yaml          # 软件级元信息与跨版本适配知识
├── README.md
├── 1.2/
└── 1.4/
    ├── conanfile.py       # 主配方：编译静态库 + 运行上游测试
    ├── conandata.yml      # 两个官方 source（主源码 + picotest 钉定 commit）+ sha256
    ├── manifest.yaml      # 版本级编译元数据
    ├── notes.md           # 本版适配笔记
    └── test_package/      # Conan L1 消费者测试
```
