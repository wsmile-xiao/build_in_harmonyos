# paml 4.10.10 适配笔记

## 编译环境
- 构建系统: makefile（上游顶层 tarball 内 src/ 子目录的 plain Makefile，无 configure、无 install target）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（来自 profile conf tools.build:compiler_executables）
- 状态: published

## 编译步骤

GitHub tag tarball 解压后布局为 `{LICENSE, README.md, Technical, dat, doc, examples, src/}`，
Makefile 与全部 C 源码在 `src/` 下：

```bash
cd src
make clean   # 防御性清理：确保不复用任何宿主构建残留（v4.10.10 tag tarball 本身不含 .o）
make -j1 CC=<clang from profile conf> CFLAGS='-O2 -Wall -Wno-unused-variable -Wno-unused-result -fPIC'
# 产物: baseml basemlg codeml evolver pamp yn00 mcmctree infinitesites chi2 ds（10 个 CLI）
```

`-j1` 根因：上游 Makefile 无 jobserver 并行安全（tools.o 为多目标共享依赖），
且 OHOS HMDFS 不支持 mkfifo，并行 make 的 jobserver 会失败。

conanfile.py 中 source() 必须显式传 `filename="paml-4.10.10.tar.gz"`：
codeload URL 无文件扩展名，conan 的 get() 无法识别 gzip 格式（报 BadZipFile）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan source() BadZipFile | codeload URL 无扩展名，get() 按 zip 解压 | source() 显式指定 filename="paml-4.10.10.tar.gz" |
| 2 | make: No rule to make target 'clean' | GitHub tarball 源码在 src/ 子目录（本地 abacus.gene 官方 tarball 是扁平布局，本地编译未暴露） | build()/package() 的目录改为 source_folder/src |
| 3 | W3 本地 CI JC full 模式拦截他人存量 dotfile | 本地无任何提交时 JC 走 full 模式整仓扫描，命中 main 上他人已跟踪的 .submit-state.json 等 | 提交 paml 变更后 JC 自动转 incremental 模式（仅扫本 PR diff），W3 通过 100% |

## 源码修改

无补丁（patches/ 为空，源码零修改）。

## 依赖版本

无 conan 依赖；仅链接系统 libm（-lm）。

## 验证结果

```bash
# conan create（OHOS aarch64 profile）: rc=0
# test_package: 4/4 用例（chi2 临界值 3.8415 断言 + yn00 端到端 ML 参考值比对 6 断言 + 10 二进制可执行
#               + 10 二进制 OHOS aarch64 ELF 平台特性），27 断言全过
# 其中鸿蒙特有断言 10 条：od 字节级校验 ELF magic(7f454c46) + ELFCLASS64(02) + e_machine(EM_AARCH64=0x00b7)
```

## 注意事项

- 上游 PAML 工具为交互式 stdin 驱动，不支持 --version/--help（L2 冒烟遥测 9/10 失败为预期，CI 标 non-blocking）
- 上游 abacus.gene 官网 tarball 与 GitHub tag tarball 布局不同（前者扁平、后者 src/ 子目录），配方以 GitHub 源为准（R39 官方源）
- 本目录无 packaging/ 产物属正常：v3.0 配方走 conan 制品仓，发布由 CI upload.sh 在合并 main 后执行

---

**编译结束**: 2026-09-03 20:10
**最终状态**: published
