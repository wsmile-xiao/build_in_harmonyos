# json-parser 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. `init-build json-parser 1.1.0 --url=https://github.com/udp/json-parser`（源码：官方 GitHub tag v1.1.0，commit 358181b530127c964962bc248014971d0d478ee2）
2. `./configure --prefix=$DEFAULT_PREFIX && make && make install DESTDIR=$TEST_PREFIX`
3. `ohc-run.py conan-init` + `conan-verify`（G0-G4/L2/L4/L5 全过）
4. `ohc-run.py finish ... built`（W2 结构 + R36 依赖 + W3 本地 CI 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 的 config.status 报 "could not setup config files machinery" (Permission denied) | HMDFS 平台坑 (E129)：新建目录固定 setgid 位，`umask 077 && mktemp -d` 产生 drwx--S--- 连属主都不可写 | 配方 build() 内联把 configure 的 `umask 077` 替换为 `umask 022`/直接 mkdir（同 4ti2/aaphoto 做法），不进入 patches/（configure 是 tarball 内生成文件） |
| 2 | conan create 的 make 阶段 llvm-ar 报 json.o 不存在 | json-parser 的 Makefile.in 用 `SRCS = $(wildcard *.c)` 只支持源内构建，conan 默认 out-of-source 构建目录为空 | 配方 `layout()` 设置 `self.folders.build = "."`（源内构建，同 abc/abduco 做法） |
| 3 | conan create 的 `make install` 阶段 jobserver mkfifo EPERM | E074：HMDFS 上并行 make 的 jobserver fifo 无法创建 | 配方 `package()` 使用 `autotools.install(args=["-j1"])` |
| 4 | test_package 运行时报 libjsonparser.so.1.0 符号找不到 | 包内同时含 .a/.so 时 CMakeDeps 的 find_library 误选 .so 且运行期加载到旧缓存坏 .so.1.0 | 配方 package() 按 shared 选项只保留一种库形态（默认 shared=False 只留静态库） |
| 5 | lang-preflight 误判为 python | 工具对全树文件名做 manifest 判定，bindings/python/setup.py（可选 Cython 绑定，辅助目录）被当主体 | 按 D.4 边界规则（辅助绑定不算主体语言）以主体验证视图复核，判定为 C（与任务 cpp 兼容族） |
| 6 | W3 本地 CI 的 JC 门禁误拦其他库（cloog/kics）历史基线 .build-closed/.staging-verified | 本地 full 模式扫描整个 git ls-files，命中 main 中已提交的其他库基线标记文件 | 按执行端基线隔离规则做 checker-input 隔离（JUNK_PR_DIFF 只含本库 PR 文件，与 CI prdiff 模式一致），基线文件未改动、未提交 |

## 源码修改

- 无源码修改；HMDFS 平台坑修复全部内联在 conanfile.py（umask/mktemp、源内构建、-j1 安装、库形态筛选），不生成 patches/（0001-configure.patch 为 refresh-patch 自动产物，未在 conandata 声明）

## 依赖版本

- 无外部依赖（纯 ANSI C，README: "no dependencies"）
- 工具链: clang 15.0.4 / conan 2.29.1 / cmake 4.1.2

## 验证结果

```bash
# 上游官方语料 29/29 全部通过（valid 13 + invalid 11 + ext-valid 3 + ext-invalid 2）
# conan-verify: G0-G4 + L2/L4/L5 全过
# W3 本地 CI: build_and_test.sh L0/L1/L4/L5 全过，conan create + test_package 通过
# test_package: json_parse 合法 JSON 成功 + 非法 JSON 拒绝（R34 实质调用 API）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（含 HMDFS 平台修复） |
| conandata.yml | 官方源码 v1.1.0 + sha256 |
| test_package/ | L1 消费者测试（R34 实质调用 json_parse） |
| manifest.yaml | 编译元数据 |

## 注意事项

- json-parser 1.1.0 主体为 ANSI C（autotools），bindings/python 为可选 Cython 绑定（辅助目录）
- 官方 tag 为 v1.1.0（commit 358181b530127c964962bc248014971d0d478ee2），本地源码包与官方 tarball 的 json.c 逐字节一致
---

**编译结束**: 2026-09-22 18:36
**最终状态**: built
