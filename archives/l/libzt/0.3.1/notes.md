# libzt 0.3.1 适配笔记

## 编译环境

- 构建系统: custom（上游 zmk/make，配方用直接编译复刻）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（HarmonyOS aarch64，OHOS profile ohos-aarch64）
- 状态: built（本地门禁通过，PR-only 交付）

## 编译步骤

1. `init-build libzt 0.3.1 --url=https://github.com/zyga/libzt/archive/refs/tags/v0.3.1.tar.gz`
   （github 直连不稳，先经 codeload 下载官方 tarball 后复用；sha256 实测
   be63cb94fda143c3abde7799d7fb38a3f282c001cbcb57c66c04fc351b84e030）
2. 上游 tag 核验: `git ls-remote --tags https://github.com/zyga/libzt` → v0.3.1 =
   24c9cd13595da5f24e37dd5b51a8cd79258e9d53（官方正式 tag）
3. lang-preflight: task=cpp / detected=c → 兼容族，通过（R47）
4. 探索编译（上游 zmk 流程）: 获取 zyga/zmk 快照 → 将 z.mk/zmk/ 并入源码树 →
   `make configure` → `./configure` → `make -j2` → `make check`（libzt-test
   自测通过，58 个测试函数）→ `make install DESTDIR=...`（staging 验证）
5. `conan-init` 生成骨架 → 重写 conanfile.py 为直接编译配方（R33 工具链注入）：
   静态 libzt.a=zt.c；共享 libzt.so.1=zt.c+libzt.map；libzt-test=zt-test.c
   （zt-test.c 内部 include zt.c，勿重复编译 zt.c，否则 duplicate symbol）
6. `conan-verify libzt 0.3.1`：G1-G4/L2/L4/L5 全过（OHOS aarch64 profile）
7. `finish libzt 0.3.1 built`：W2 结构检查、R36 依赖检查、W3 本地 CI 模拟通过
   （.ci-result.json exit_code=0，log_sha256=d2318bb3...）；test_package
   MANIFEST.yml 声明上游测试；reports/test-report.md 记录 58 用例全过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时/不稳 | worker 网络无法直连 github（curl/git 均失败，python urllib 偶发可达） | 用 codeload.github.com 下载官方 v0.3.1 tarball；conan-verify E017 自动注入 ghfast.top 镜像 |
| 2 | init-build 报"下载内容是 HTML" | 传入仓库页 URL 而非 tarball URL | 改用 /archive/refs/tags/v0.3.1.tar.gz 完整 URL |
| 3 | zmk `make configure` 报 unsupported operating system kernel HarmonyOS | zmk OS.mk 只识别 Linux/Darwin/Windows 等，uname -s=HarmonyOS 未收录 | zmk/OS.mk ELF 内核列表加入 HarmonyOS（本地探索构建用，配方直接编译不依赖 zmk） |
| 4 | libzt-test 链接 duplicate symbol: zt_pack_rune 等 | zt-test.c 内部 `#include "zt.c"`，与显式编译的 zt.c 重复 | 配方只编译 zt-test.c（与上游 libzt-test.Sources=zt-test.c 一致） |
| 5 | test_package 编译失败 | 误用 README 旧示例 API（ZT_CMP_STR/ZT_VISIT_TEST/v.value/zt_value_nothing） | 按 zt.h 0.3.1 实际 API 改写：ZT_CMP_CSTR/ZT_VISIT_TEST_CASE/v.as.integer/ZT_NOTHING |
| 6 | W3 JC junk 拦截 | 无关历史基线 cloog/kics 的空标记文件（.build-closed/.staging-verified）被全仓扫描拦截 | 按 ohpc-executor 规则做临时 checker-input 隔离（git rm --cached 精确路径），W3 复验通过后无条件恢复（blob e69de29） |

## 依赖版本

- 无 Conan 依赖（纯 C 单文件库，zt.c + zt.h）
- 构建工具: clang 15.0.4、llvm-ar、make

## 验证结果

- 上游测试: make check → libzt-test 58 测试函数全过（exit 0）
- conan-verify: 通过
- W3 本地 CI 模拟: 通过

## 交付物

- archives/l/libzt/0.3.1/conanfile.py（直接编译配方，shared/static 双模式）
- archives/l/libzt/0.3.1/conandata.yml（官方源 + sha256）
- archives/l/libzt/0.3.1/test_package/（真实 API 消费者测试 + MANIFEST.yml）
- archives/l/libzt/0.3.1/reports/（conan-verify 报告 + test-report.md）
- archives/l/libzt/0.3.1/manifest.yaml（status: built）

## 注意事项

- 上游发布 tarball 不含 z.mk（zmk 构建系统需单独获取），配方直接编译规避
- PR 仅含 archives/l/libzt/0.3.1/**；libxext 大小写串扰文件绝不 git add

**编译结束**: 2026-09-21
**最终状态**: built
---

**编译结束**: 2026-09-26 17:59
**最终状态**: built
