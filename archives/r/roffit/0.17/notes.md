# roffit 0.17 适配笔记

## 软件简介

roffit 是 Daniel Stenberg 开发的单文件 Perl 脚本工具，将 nroff/troff 格式的
man page 转换为 HTML（curl 项目文档工具链成员）。纯脚本工具，无需编译。

## 编译环境
- 构建系统: 无构建（Makefile 仅 install/test 目标）
- 编译日期: 2026-10-02
- 运行时解释器: perl/5.42.2.3（ohpcd 制品仓预编译包）
- 状态: published

## 编译步骤

1. 无编译步骤：`package_type = application`，`build()` 仅应用补丁。
2. `package()` 打包 `roffit` 脚本（bin/）、`roffit.1`（share/man/man1/）、LICENSE。
3. shebang 修复：上游 `#!/usr/bin/env perl` 在 OHOS 上本可工作，但为与
   abcselect 先例一致并确保经 Conan runenv PATH 解析，package() 统一改写为
   `#!/usr/bin/env perl`（上游本身即 env 形式，无需变更）。
4. 运行时依赖：`self.requires("perl/5.42.2.3")`（制品仓已有完整二进制，
   本机 conan download 验证 v5.42.2 aarch64 可执行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't locate HTML/Entities.pm` | HTML::Entities 属 CPAN HTML-Parser 模块，非 perl 核心模块；ohpcd perl 包不含 | 补丁 0001：用纯 Perl 正则替换实现 `encode_entities($s, q{<>&"'#})` 等价逻辑，输出与上游基准字节级一致（testpage 黄金文件比对通过） |
| 2 | lang-preflight 误报 mixed | 工具将顶层 Makefile 判为 "c manifest"，与 100% perl 源码统计冲突 | 误报（源码统计 perl:1 占比 100%，Makefile 非 C 语言 manifest），人工复核为纯 Perl 工具，参考 abcselect 先例继续适配，本笔记记录判定依据 |
| 3 | CI（PR #14304，worker 033）conan create 源码下载超时 | worker 网络无法直连 github.com，且 worker 无 curl（CI 预下载脚本 curl: FileNotFoundError 全失败），conan 直连官方源 ConnectTimeout | 知识库 E017：conandata.yml url 列表追加 gh-proxy.com 镜像 fallback（与 build_and_test.sh get_mirrors 同源），conan get() 逐个尝试，官方超时后自动回落镜像；同时清理 conandata.yml.ghfast-bak 残留（JC1） |

## 源码修改

- 仅 `roffit` 一处：删除 `use HTML::Entities qw(encode_entities);`，
  `do_encode()` 改为纯 Perl 实现（补丁由 refresh-patch --auto 生成：
  patches/0001-roffit.patch）。
- 转义语义：`& < > " ' #` 七字符转义，与 HTML::Entities 指定字符集行为
  完全一致（`&#39;`/`&#35;` 数字实体），testpage.output 比对字节级相同。

## 测试说明（R51 上游测试三步法）

- 上游测试清点：仓库唯一测试 = `Makefile test` 目标，1 个黄金文件用例
  （`perl roffit --bare < testpage.1` 与 `testpage.output` 逐字节 cmp），
  由上游 CI（.github/workflows/test.yml）执行。
- 本地实测：`make test` → SUCCESS（1/1，100%）。
- test_package 复现上游用例（用 perl 依赖解释器执行打包后的 roffit 并与
  打包内附带的 testpage.1/testpage.output 比对），另加 --version 与 man 页
  存在性断言，共 3 项断言。

## 语言预检说明（R47）

lang-preflight 判 detected=mixed 并写 env_unsupported——为工具误报：其
"manifest" 级判定把 Makefile 当作 C 语言 manifest，而源码统计为 perl 100%。
roffit 实为纯 Perl 脚本工具（同已合入的 abcselect 1.5 先例），本包按 Perl
CLI 工具模式适配，符合仓库既有实践。
---

**编译结束**: 2026-10-02 13:15
**最终状态**: published
