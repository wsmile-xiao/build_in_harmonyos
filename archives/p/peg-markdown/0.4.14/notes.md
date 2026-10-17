# peg-markdown 0.4.14 适配笔记

## 编译环境
- 构建系统: makefile（顶层只有一个 GNU Make Makefile，**没有 configure / Makefile.in / CMakeLists**）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（`Target: aarch64-unknown-linux-ohos`）；`gcc` / `cc` 在 worker 上不存在（exit 127）
- 状态: built → conan-verify 通过后升级 published

## 源码与上游测试入口核验

| 项 | 事实 | 证据 |
|---|---|---|
| 官方源 | `https://github.com/jgm/peg-markdown/archive/refs/tags/0.4.14.tar.gz`；本 worker 上 github.com 直连超时，改由 codeload.github.com（同为 GitHub 官方归档主机）取回，二者内容同一 | sha256 `111bc56058cfed11890af11bec7419e2f7ccec6b399bf05f8c55dae0a1712980`（`logs/01-fetch-source.log`） |
| 发布说明 | GitHub Releases 列表为空 `[]`，无 CHANGELOG 文件；`0.4.14` 是最新 tag（commit 2012-11-07 "Bump version to 0.4.14."），上游已停更 | `logs/`（api.github.com/releases、/tags、/commits/0.4.14） |
| 已有配方 | 本仓 archives、ohpcd 制品仓、conan-center-index 均无 peg-markdown 配方 | `conan download peg-markdown/0.4.14 -r=ohpcd --only-recipe` → exit 1（与不存在对照包同报错） |
| 构建依赖 | `pkg-config glib-2.0`（Makefile:27,30）+ GNU make + patch；PEG 生成器 peg/leg 以 `peg-0.1.4/` 形式内嵌在源码包内，构建期自动编译（README:33-40） | `logs/02,26` |
| 测试入口 | `make test` → `cd MarkdownTest_1.0.3 && ./MarkdownTest.pl --script=../markdown --tidy`；用例 = `Tests/*.text` 22 个（.text/.html 一一配对）；另有 `leak-check`（valgrind，非默认目标） | `Makefile:43-48`、`logs/32` |

## 编译步骤（探索阶段，`logs/26,27,30,32,35`）

```bash
conan install --requires=glib/2.84.0.2 -g PkgConfigDeps -g AutotoolsToolchain -b never \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64     # 取依赖与可用的 glib-2.0.pc
make                # ← 上游原样构建，失败于 CC=gcc（见问题 2）
make peg                                  # 生成 peg/ 目录并应用上游自带两个 peg 补丁
make -C peg CC=clang                      # 用 clang 构建主机工具 peg/leg
make CC=clang PKG_CONFIG=pkg-config       # leg 已就绪 → 生成 markdown_parser.c 并编译链接 markdown
mkdir -p $TEST_PREFIX/bin && cp -p markdown $TEST_PREFIX/bin/    # 上游无 install 目标（见问题 3）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./markdown <file>` 与 `echo … \| ./markdown` 永久挂死（首次探索构建 exit 超时 339s） | `markdown.c:60 char curchar;` 用 `char` 接收 `fgetc()`。AArch64 ABI 下 `char` 默认 **无符号**，`fgetc()` 返回的 EOF(-1) 被截断，`!= EOF` 恒真 → 读取循环永不退出。clang 已给出告警 `-Wtautological-constant-out-of-range-compare`（2 处） | 补丁 `patches/0001-markdown.c.patch`：`char curchar` → `int curchar`（POSIX 正确写法，无平台宏，非 `#ifdef` 空壳）。修复后 2 条告警消失、stdin/文件两条路径均 exit=0（`logs/30,31`），并被 test_package 作为回归护栏 |
| 2 | `make` 失败：`make[1]: gcc: No such file or directory`，`*** [Makefile:24: peg/leg] Error 2`（exit 2） | 顶层 Makefile 第 24 行硬编码 `CC=gcc make -C peg` 构建内嵌 PEG 生成器；README 也自陈 "seems to require gcc"。鸿蒙 worker 只有 clang | 配方 build() 先 `make -C peg CC=<conan cc>` 显式用 clang 建出 `peg/leg`；随后顶层 `make` 的 gcc 分支只剩 "Nothing to be done for 'all'"，不再调用 gcc（`logs/27,30`）。不改源码、不加平台宏 |
| 3 | `make install` 不存在 | 0.4.14 的 Makefile 只有 ALL/clean/distclean/test/leak-check 目标，无 install、也无库目标 | 配方 package() 直接 `copy("markdown", build_folder → bin/)` + LICENSE；`package_type=application`，`cpp_info.bindirs=["bin"]`，includedirs/libdirs 置空 |
| 4 | `pkg-config --cflags glib-2.0` 报 `Package 'libpcre2-8' … not found`，或给出 `-I//include/glib-2.0` 废路径 | 制品自带的 `glib-2.0.pc` 里 `prefix=/`（面向设备根文件系统），且其 `Requires` 指向未在同一 PKG_CONFIG_PATH 的兄弟 .pc | 配方使用 `PkgConfigDeps`（生成指向包内真实路径的 `glib-2.0.pc`）+ `AutotoolsToolchain`（把 PKG_CONFIG_PATH 注入 conanbuild 环境）；实测 `pkg-config --cflags --libs glib-2.0` exit=0（`logs/10,25`） |
| 5 | `make test` 报 `/bin/sh: ./MarkdownTest.pl: No such file or directory`（exit 126） | 测试脚本 shebang 是 `#!/usr/bin/perl`，鸿蒙 perl 在 `/data/service/hnp/bin/perl`，`/usr/bin/perl` 不存在 | 不改上游测试脚本，显式经解释器调用：`perl ./MarkdownTest.pl --script=../markdown --tidy`（exit 0，`logs/32`） |
| 6 | 测试需要 `tidy` CLI（`--tidy` 模式），worker 上没有 | `MarkdownTest.pl:73-74` 调外部 `tidy`；系统未装 | 消费制品仓 `tidy-html5/5.8.0` 的 `bin/tidy`（`conan download tidy-html5/5.8.0:*` exit=0），仅测试期使用，不进本包依赖 |

## 遗留的框架侧问题（本包不修，留待主编/框架 PR）

| # | 现象 | 证据 | 影响 |
|---|---|---|---|
| A | `finish`/W3 跑完后 `conandata.yml` 会残留 CI 注入的镜像 URL（`url:` 变成 `[gh-proxy.com/…, 官方]` 列表），`conandata.yml.ghfast-bak` 也随之留下 | 第二次 finish 后 `archives/p/peg-markdown/0.4.14/conandata.yml:4` 出现 `https://gh-proxy.com/https://github.com/...`；PF7 当场报 R39 违规（`logs/47`）。手工还原后复验 PF7=PASS（`logs/49`） | 提交前必须由 AI 手工还原官方 URL；建议 build_and_test.sh 的 pre-download 备份点应在 conan_verify 注入之前，或 restore 时按“去镜像”规范化 |
| B | PF9 与 R38/PF8 冲突：CLI 包必须提供**软件级** `archives/<l>/<pkg>/commands.json`（R38、PF8、CI L0k），而 PF9 以 `len(path.split('/')) < 5` 判定“变更路径缺版本目录层”，把软件级文件一律拦下 | `scripts/ohc/preflight.py:check_branch_and_paths`；本包 PF1/PF2/PF3/PF4/PF5/PF6/PF7/PF8 全 PASS，唯 PF9 报 `archives/p/peg-markdown/README.md, commands.json`（`logs/49`）。先例：aqua v2.60.0（commit 7eb110962b，2026-09-08，PF9 上线之后）同一提交同时含软件级 README.md/commands.json 并已入库 | 新建 CLI 包的配方 PR 无法在建 PR 前同时满足 PF8 与 PF9；需主编修正 PF9（豁免软件级 README.md/commands.json/manifest.yaml） |
| C | `finish` Step 8 `gen_summary` 抛 `'str' object has no attribute 'append'` | 逐文件复现：仅 `archives/q/qpdf/12.3.2/manifest.yaml`、`archives/q/qpdf/12.3.2.1/manifest.yaml` 触发（5371 个 manifest 中 2 个），本包 manifest 解析正常 | 非本包引入；SUMMARY.md 无法再生成，属存量数据+朴素 YAML 解析器缺陷 |
| D | `ohc-run.py graph add` 报告的“下一个可用 ID”（E429）与 `knowledge/graph/` 实际占用及 `index.tsv` 最大值（E542）不一致；草稿目录里同一 `E###-draft-<AgentID>` 编号被多包并发复用 | `ls knowledge/drafts` 中 E543-* 已有 20+ 个不同内容的 tracked 草稿 | 草稿编号仅供人工 promote 时参考，不构成正确性问题，但建议 graph add 以 index.tsv 与已占用草稿号取并集分配 |

## 知识沉淀对应

| 现象 | 图谱条目 | 说明 |
|---|---|---|
| `char` 承接 `fgetc()` → EOF 恒不等、读入死循环 | 正式条目 **E419**（plain char 符号性）+ 新建草稿 **E547** | E419 首选方案是 toolchain 加 `-fsigned-char`；本包改用 **`int` 声明（E419 的 fallback：upstream-explicit-signed-type）**。理由：`fgetc()` 的返回类型本来就是 `int`，用 `int` 是 POSIX 正确写法且零平台假设；`-fsigned-char` 只是让 `char` 恰好能表示 -1，仍依赖实现定义行为，且会给纯字节处理代码带来符号扩展副作用。差异已如实登记，不做静默偏离 |
| 上游硬编码 `CC=gcc` 建内嵌主机工具 | 草稿 **E546** | 先 `make -C peg CC=<conan cc>` 绕开 |
| `tools.build:compiler_executables:c` 子键查询异常 | 草稿 **E544** | conf 是 dict，需整体取后 `.get("c")` |
| in-tree Makefile 在 build_folder 找不到 Makefile | 草稿 **E545** | `self.run(cwd=self.source_folder)` |
| toybox grep 不支持 BRE `\|` → 断言假失败 | 草稿 **E543** | 测试脚本一律 `grep -qF` / `-qE` |

## 上游测试实跑（R51）

清点：`MarkdownTest_1.0.3/Tests/` 共 22 个 `.text`，均有同名 `.html` 期望文件 → 22 个用例；无 ctest/pytest 注册项。

实际执行命令（构建期主机环境）：

```bash
cd MarkdownTest_1.0.3 && perl ./MarkdownTest.pl --script=../markdown --tidy
```

结果：**21 passed / 1 failed / 0 skipped**（exit=0，脚本本身不对失败置非零码）。逐用例明细见 `reports/upstream-test.md`。

唯一失败 `Ordered and unordered lists` **不是本次适配引入的回归**，是上游文档化的预期失败：
- `README.markdown:53-66`：“The test suite will fail on one of the list tests.”（peg-markdown 对列表项段落的 `<p>` 包裹策略与 Markdown.pl 不同）
- 上游 issue #6 标题即 “Ordered and unordered lists fails in `make test`”，报告人贴出的输出与本仓实测逐行一致（同一 diff、同一 `21 passed; 1 failed`），作者 jgm 回复 “This failure is expected and documented in the README.”（证据 `logs/34-upstream-issue6.log`）

对照实验：去掉 `--tidy` 后为 9 passed / 13 failed（差异来自空白与换行归一化），故 `--tidy` 才是上游定义的可比较口径（`logs/33`）。

## 依赖版本

| 依赖 | 版本 | 用途 | 消费方式 |
|---|---|---|---|
| glib | 2.84.0.2 | 编译+运行链接（`-lglib-2.0`） | `self.requires`，制品仓预编译 binary |
| pcre2 / zlib / libffi | 10.45 / 1.3.1.1 / 3.4.4 | glib 的传递依赖 | 由 glib 配方带入，均已发布 |
| tidy-html5 | 5.8.0 | 仅上游测试 `--tidy` 归一化 | 测试期取制品仓二进制，不作包依赖 |
| perl | 设备自带（5.x，`/data/service/hnp/bin/perl`） | 仅上游测试驱动 | 测试期使用 |

## 验证结果

```text
./markdown --version                        → peg-markdown version 0.4.14            exit=0
printf '# hi\n\n*em*\n' | ./markdown        → <h1>hi</h1> <p><em>em</em></p>          exit=0
./markdown README.markdown | head           → <h1>What is this?</h1> ...              exit=0
staging: $TEST_PREFIX/bin/markdown --version → 同上                                    exit=0
make test (perl + tidy)                     → 21 passed; 1 failed（上游预期失败项）    exit=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/markdown | 301440 B | CLI（aarch64 ELF，动态依赖 libglib-2.0.so.0） |
| licenses/LICENSE | 4 KB | 双许可 MIT / GPLv2+ 原文 |

## 注意事项

1. 上游 0.4.14 **不提供库产物**（无 install、无 libmarkdown 目标），故本包按 CLI 交付；需要 `markdown_to_string()` API 的下游应自行推动上游/派生版本，勿在此配方里发明库目标。
2. `peg/leg` 是构建期主机工具。当前 worker 上 build==host（原生 OHOS clang），配方直接复用 conan 的 C 编译器；若将来引入真交叉编译（build ≠ host），需改为 `tool_requires` 提供原生 leg 或先产出 host 二进制。
3. 上游 Makefile 的 `$(PEGDIR)` 规则会顺带把 `peg-exe-ext.patch` 打到 `peg-0.1.4/Makefile`（而构建用的是 `peg/` 副本，副本未打该补丁）——上游自身的目录名不一致 quirk，在 Unix 下无影响（`X` 为空），适配未额外处理。
4. `CFLAGS ?= -Wall -O3 -ansi` 会被 conan 注入的 CFLAGS 覆盖（`-fPIC -O2`），因此不再启用 `-ansi`(c89)；这与修复 1 无冲突，且避免了 c89 与 musl 头文件的摩擦。
---

**编译结束**: 2026-09-09 00:14
**最终状态**: built
