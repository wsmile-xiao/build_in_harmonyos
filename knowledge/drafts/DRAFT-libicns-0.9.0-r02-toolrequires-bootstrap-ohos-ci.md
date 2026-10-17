# DRAFT — tool_requires bootstrap + 双 perl 协调（libicns 0.9.0 r02）

## 现象 (What happened)

libicns 0.9.0（kornelski/libicns master，固定 commit）源码**不含任何生成式
Autotools 文件**，且上游**无 git tag / release tarball**（codeload tags 全
404、`api.github.com/repos/kornelski/libicns/tags` = `[]`），只能取 master
源码。配方 build() 必须自行 bootstrap（aclocal → autoconf → autoheader →
libtoolize → automake）。

远端 CI（PR 10905，conan-build-test）L1 首个真实错误：

```
libicns/0.9.0: Error in build() method, line 111
  self._bootstrap_autotools()
  self.run("aclocal --force", cwd=source, env="conanbuild")
  ConanException: Error 127 while executing
/system/bin/sh: aclocal: inaccessible or not found
```

OHOS CI 构建沙箱 PATH 中**没有** automake/aclocal/libtool。本地设备虽有
system automake（~/usr/local/bin，1.16.5）可解析到 aclocal，但随即暴露
**第二层 perl 解释器冲突**：

```
Can't load '.../perlbad96edf51f7f/p/lib/perl5/5.42.2/aarch64-linux-thread-multi/
  auto/Cwd/Cwd.so' for module Cwd: Error relocating ... Perl_my_cxt_init: symbol
  not found
```

以及去掉 conan perl lib 后的反向失败：`Can't locate strict.pm in @INC`
（.autom4te-real）。

## 根因 (Root cause)

1. **源码无生成式 configure**：GitHub archive（master tarball）从不含 autotools
   产物，配方必须 bootstrap；E058/E059 的 use-stable-release 方案在此**不可用**
   （上游根本没有 release 归档可选）。
2. **CI 沙箱无系统 autotools**：OHOS CI 的 PATH 不含 automake/aclocal/libtool，
   裸调 `aclocal` exit 127。
3. **双 perl 解释器**：automake/autoconf 包装脚本的 `-real` payload shebang
   不一致——`.aclocal-real`/`.automake-real` 指向 device perl（
   /data/service/hnp/bin/perl，v5.42.0 非 thread-multi），而
   `.autom4te-real`/`.autoconf-real` 与 perl tool_require 指向 conan perl
   （5.42.2 aarch64-linux-thread-multi）。前者环境里 PERL5LIB 若混入 conan perl
   的 thread-multi XS，加载 Cwd.so 即 `Perl_my_cxt_init: symbol not found`；
   若把 PERL5LIB 清掉只留 share 目录，conan perl 解释的 autom4te 又缺
   strict.pm。

## 解法 (Fix)

| # | 动作 | 说明 |
|---|------|------|
| 1 | `build_requirements()` 加 tool_requires | `autoconf/2.72`、`automake/1.18`、`libtool/2.5.4`、`m4/1.4.19`（先 `conan download --only-recipe -r=ohpcd` 实测可消费，RC=0） |
| 2 | bootstrap 命令走 *tool env | 引用 `$ACLOCAL/$AUTOMAKE/$AUTOCONF/$AUTOHEADER/$LIBTOOLIZE/$PERL`，不裸调 PATH 命令（设备 system automake 会遮蔽） |
| 3 | aclocal/automake 直接以 `$PERL` 调 payload | `"$PERL" <conan-automake>/bin/.aclocal-real --automake-acdir=<pkg>/share/aclocal-1.18 --system-acdir=<pkg>/share/aclocal`；automake 同理 `--libdir=<pkg>/share/automake-1.18`（绕过 device perl shebang） |
| 4 | PERL5LIB 保留 conan perl lib + 追加 share | `PERL5LIB="${PERL5LIB:+$PERL5LIB:}<automake>/share/automake-1.18:<automake>/share/aclocal-1.18:<autoconf>/share/autoconf"`（两种 perl 各自的核心/XS 与 autotools 的 perl 模块都能解析） |
| 5 | configure umask 077 → 022 | 全量替换（站点数随 autoconf 版本 2/3 不定，不设固定 count 契约），HMDFS 兼容 |

## 与既有知识的关系 (vs existing knowledge)

| 条目 | 覆盖部分 | 本条新增部分 |
|------|---------|-------------|
| E058 / E059 | 源码缺生成 configure/aclocal.m4 → use-stable-release | 上游无 release 可选时改走 tool_requires bootstrap 路径 |
| E071 | automake 版本不匹配 → bypass-autotools-env | 解决的是"工具缺失"而非"版本不匹配"；注入方式是 tool_requires 而非 env 绕过 |
| E540 | OHOS profile 后续命令 PATH 缺 hnp bin → runner-path-prepend | 本条是构建工具缺失（可 tool_requires 补给），E540 是运行时 PATH（不可整体补给） |
| DRAFT-E2186 | autotools 依赖 flags 缺失 | 互补（flags vs 工具链），非重叠 |
| （无条目） | 195 个配方已用 tool_requires("automake/1.18") | 知识库此前无条目标记此模式——首个系统化记录 |

## 验证 (Verification)

- 远端 CI 首错（aclocal exit 127）本地按 CI profile 复现。
- 修复后：`conan-verify` G0-G4 + L2/L4/L5 全 PASS（conan_verify9.log）；
  W3 本地 CI 模拟 JC_RESULT=pass / L0 pass / 100%（incremental 13 文件）；
  test_package 消费者 test_libicns + 鸿蒙专项 test_ohos_libicns 实跑
  "all checks passed"；提交前扫描无 gh-proxy/ghfast/file:///本地路径残留。

## 适用边界 / 反例 (Boundaries)

- 适用：GitHub archive 源码无生成式 autotools 文件的包 + OHOS CI 无系统
  autotools；或设备有 system automake 但被遮蔽/版本不匹配。
- 反例/边界：上游存在带 configure 的 release 归档时，直接取 release 最简
  （E058/E059 路线）；仅版本不匹配时走 E071；仅运行时 PATH 缺口走 E540。
- cln 类 mktemp 恒 0700 场景仍需 DRAFT-6507 的 mkdir -m 0777（与本条 umask
  022 处方互不替代，先实测再选路）。