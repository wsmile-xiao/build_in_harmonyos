# huffman 1.2.7 适配笔记

## 编译环境
- 构建系统: makefile（上游裸 Makefile，无 configure、无 install target）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 / llvm-ar
- 状态: built

## 编译步骤

1. 核验上游来源：官方标签 `v1.2.7`，commit `102150ac8ca5d5b8aa4a9ddd897a98e6793b8342`（GitHub API 核验）。
2. 源码包 SHA-256：`b7fa4c52fbebe2e6d573350d6b64faaec4216beeb78d1fc25ce74e6a9a756a6c`
   （codeload 与官方 archive/refs/tags/v1.2.7.tar.gz 两处下载一致，gh-proxy 镜像复验）。
3. `make -j1 CC=clang AR=llvm-ar` → 产出 `libhuffman.a` + `huffcode`。
4. 上游测试：`bash run_tests.sh` → "All Tests Passed"（9 组压缩-解压往返 + 14 个 issue2 回归）。
5. conan 配方：Makefile 版 conanfile.py（library 类型），package() 复制
   `libhuffman.a → lib/`、`huffman.h → include/huffman/`（与上游 CMakeLists 安装路径一致）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make check` 报 `./run_tests.sh: No such file or directory` | OHOS 无 `/bin/bash`，脚本 shebang 无法解析 | recipe 与测试均显式 `bash run_tests.sh` |
| 2 | init-build 下载 GitHub 主站超时 | 本机 github.com 直连不可达 | 源码经 codeload/gh-proxy 获取；conandata 保留官方 URL，CI 镜像 fallback 自动注入 |
| 3 | conan-init 生成 autotools 模板 | 上游实为裸 Makefile 工程 | 按 conanfile-makefile 规范重写配方 |

## 源码修改

无（未应用补丁）。

## 依赖版本

无第三方依赖（纯标准 C11）。

## 验证结果

```bash
$ make -j1 CC=clang AR=llvm-ar          # exit 0
$ bash run_tests.sh                     # All Tests Passed, exit 0
$ ./huffcode -i test_data/3_line -o /tmp/x.huf && ./huffcode -d -i /tmp/x.huf -o /tmp/x.raw && diff /tmp/x.raw test_data/3_line   # exit 0
```

## 注意事项

- 上游为纯 C 库 + huffcode CLI，按 library 打包；CLI 工具 huffcode 不入包
  （commands.json 仅 tool 类型需要，本配方 package_type=library 且不装 bin）。
- 归档路径与上游 CMakeLists 的 include/huffman 安装路径保持一致。
---

**编译结束**: 2026-09-22 17:10
**最终状态**: built

## 知识判定（task_id: huffman-1.2.7-r01-bootstrap-and-adapt-pc3-11-20260922T083950Z）

- 快照: /storage/Users/currentUser/tianyi/.ohpc-kn-snapshots/huffman-1.2.7-r01-bootstrap-and-adapt-pc3-11-20260922T083950Z
  (knowledge repo main @ 48d9cee6844d0fca1f25e86c2df1293b904855d8, sparse=knowledge, 外置只读)
- 候选 1: OHOS 无 /bin/bash，上游 make check (run_tests.sh shebang) 无法执行
  → 等价命中正式条目 **E165**（error_signature `#!/bin/bash|bad interpreter: /bin/bash`,
    root_cause 一致，rec_approach shebang-fix；本轮以 recipe 内 `bash run_tests.sh` 显式调用落地）
- 候选 2: 裸 Makefile 无 install target，package() 手动复制 libhuffman.a + huffman.h
  → 被既有草稿 **DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package**（manual package 模式）
    与 **DRAFT-commander-1.4.0-makefile-recipe-build-package-traps**（裸 Makefile 配方陷阱）覆盖，逐字段适用
- 候选 3: GitHub 主站直连不可达（init-build 下载失败）
  → 基础设施/网络类，由 E017（github URL 镜像注入 ghfast.top/gh-proxy）覆盖；永不路径 B
- 判定: **knowledge_decision: reuse_existing（路径 A）**；无等价命中之外的跨库新增价值，
  未创建 DRAFT-huffman-*.md/.kv 草稿；正式 E###/索引/其他库目录未写入。
