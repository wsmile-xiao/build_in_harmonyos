# jmeters 0.4.5 适配笔记

## 编译环境
- 构建系统: makefile（上游唯一构建文件 = source/Makefile，无 configure / 无 CMake / 无 autotools）
- 编译日期: 2026-09-26
- 编译器: clang/clang++（Conan profile ohos-aarch64，conf tools.build:compiler_executables）
- 设备: HarmonyOS PC（B 机，aarch64），CONAN_HOME tmp/ch/home-jmeters-64
- 状态: built（`ohc-run.py finish jmeters 0.4.5 built` 于 2026-09-26 06:29 落地，见下节 W3 读数）

## 源码获取（官方直链，R39）
- URL: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jmeters-0.4.5.tar.bz2
- curl -4 -I -> HTTP/1.1 200 OK，Content-Length 298619，ETag "48e7b-5744321f6b340"
- 自算 sha256: 1f37d1c4783bb9381ff865a98ed98369b03e280b5629f6bb4a1c5f864bf4becc（bzip2 -t 通过，size 298619）
- ⚠ 上游可达性间歇：不带 -4 的连接多次 60s 超时（curl rc=28），带 -4 首次即成功；
  该域名无 AAAA 记录。init-build 的 urllib 下载臂同样出现过 Errno 110。
- `conandata.yml` 只有官方直链，无任何镜像前缀（自查读数：`grep -c ghfast` = 0、`grep -c mirrors` = 0）。

## 依赖（W0 发布态实测，conan download <ref> -r=ohpcd --only-recipe 均 rc=0）
clxclient/3.9.2、clthreads/2.4.0、jack/1.9.22、libsndfile/1.2.2、libpng/1.6.58、
cairo/1.18.4.1、freetype/2.14.3、libxft/2.3.8、libx11/6.4.0、libxext/6.4.0、fontconfig/2.18.3。
说明：libpng/1.6.50 探测报 ERROR: error:system acceleration policy not enabled（非"未发布"读数），
同族已合入配方固定用 1.6.58；cairo 固定 1.18.4.1（同族 zita 用法）。

## 上游 make 目标与测试
- 目标：all / jmeters / install / uninstall / clean —— 无 check/test/TESTS，无 *.t、无 ctest/autotools 测试。
- LDLIBS: -lsndfile -lclxclient -lclthreads -ljack -lpthread -lcairo -lpng -lXft -lX11 -lrt
- 目标 jmeters 额外 CPPFLAGS 取 $(shell pkgconf --cflags freetype2)（OHOS PATH 无 pkgconf，需注入 include 目录）

## 已识别的同族先例与移植点
- archives/z/zita/0.2.2（同作者、同裸 Makefile、依赖集几乎一致）= 首稿移植母本
- archives/a/aeolus/0.10.4、archives/a/aliki/0.3.0（同族 Makefile + jack/clxclient）
- knowledge/drafts/DRAFT-8958-clthreads-makefile-stage-install-shadow.md（install 遮蔽 + HMDFS symlink + -march=native）
- knowledge/drafts/DRAFT-8543-refresh-patch-rename-conandata-desync.md（同一 refresh-patch 管线的"改名/重置分类"相反面）
- knowledge/graph/E088.kv:2（musl namespace 忽略 RUNPATH/LD_LIBRARY_PATH —— 用于下面"运行时边界"定性）
- 移植点：去 -march=native；install -> $(INSTALL)/INSTALL=/bin/install；-DCLTHREADS_NO_PTHREAD_CANCEL；
  依赖 include/lib 经 CPPFLAGS/LDFLAGS 注入；package 阶段 PREFIX=/ 使 bin/ 与 share/jmeters/ 落到包目录。
- ⚠ 上游 install 规则引用 ../share/*，必须保持 source/ 与 share/ 兄弟目录结构（zita notes 记录 init-build 的
  嵌套源码提升会破坏该引用）。

## 上游测试五维账本（R51，分母不缩）
| 维度 | 静态读数（命令与结果） | 执行读数 |
|---|---|---|
| `TESTS` / ctest 注册 | `grep -n 'TESTS\|check\:' source/Makefile` → 0 命中；无 CMakeLists.txt | 0 项 |
| `make check` | 上游目标只有 all / jmeters / install / uninstall / clean；`make -n check` → `No rule to make target 'check'` | 目标不存在，未执行 |
| 单元/回归测试文件（`*.t`、`test*`） | `find . -name '*.t' -o -name '*test*'` → 0 个文件（上游只发 README/COPYING/AUTHORS/source/share） | 0 项 |
| autotools/meson 测试链 | 无 configure.ac / Makefile.am / meson.build | 不适用 |
| test_package 消费者测试 | `test_package/test_jmeters.c` 4 项确定性断言（见 test_package/MANIFEST.yml） | 4/4 通过；用例级 1/1，`conan test` 进程 rc=0 |

### 上游静态合计的「审查实测口径四式」（对纯净树 `~/tmp/builds/jmeters-0.4.5.orig` 跑，逐字读数）

| # | 形态 | 命令 | 实测原文 |
|---|---|---|---|
| 1 | 独立测试框架源码 | `find $O -name '*.t' -o -iname '*test*' \| wc -l`；`find $O -name '*.c' \| wc -l` | `0`；`0`（整棵上游树**没有任何 .c 文件**，源码全为 `.cc/.h`） |
| 2 | `res` 语料目录 | `find $O -type d -name res \| wc -l` | `0`（`share/` 有 21 个文件，全部是 `-meter/-scorr` 皮肤 PNG，属运行期皮肤资源，不是测试语料） |
| 3 | `*RUNTEST*` 脚本 | `find $O -iname '*RUNTEST*' -print`；`... \| wc -l` | 无输出行；`0` |
| 4 | `src/demo` / `examples` 示例目录 | `find $O -type d -name demo -o -type d -name examples`；`find $O \( -path '*/demo/*' -o -path '*/examples/*' \) -name '*.c' \| wc -l` | 无输出行；`0` |

⇒ **上游测试资产静态合计 = 0**（四式 + `TESTS`/ctest 注册 + `make check` 六路读数一致为 0），
申报口径为 0 不是"未清点"：本包上游 0.4.5 连测试目标都没有，`make -n check` 直接 `No rule to make target 'check'`。
未使用任何 `--disable-*` 之类的减分手段。

### 测试账本两表（供 PR 正文直接引用）

上游库测试用例统计：

| 形态 | 实测 | 说明 |
|---|---|---|
| 独立测试框架源码 | **0** | 上游无 `test/`、无 `*.t`、无 .c 文件 |
| 测试语料目录 | **0** | 无 `res` 目录；`share/` 21 个 PNG 是皮肤资源 |
| `*RUNTEST*` 脚本 | **0** | 无 |
| `src/demo`/`examples` 示例 | **0** | 无 |
| **合计** | **0** | 上游 0.4.5 未发布任何测试资产 |

适配后测试用例统计：

| 用例 | 结果 | 说明 |
|---|---|---|
| `test_package/test_jmeters.c` | **1/1** 通过（进程 rc=0） | 含 4 项检查点 / 5 处 `check()` 调用（:223、:230、:235、:253、:261） |
| 鸿蒙特有测试 | **0** | 本包无平台专属用例；OHOS 运行面判据由 `test_jmeters.c:235`（AArch64 小端 ELF 头）、`:261`（DT_NEEDED 链在 `LD_LIBRARY_PATH` 各目录逐项 `access(R_OK)` 命中）与 `:253`（版本字面量内嵌）三条断言承担，不重复计数 |
| **合计** | **1** | 1 ≥ 上游静态合计 0 |

## 验证结果（第 1 轮，B 机真机，conan 2.29.1 / profile ohos-aarch64）
- 第 1 次 `conan-verify`（round2-verify-r1.log）= **G2 FAIL，VERIFY_RC=2**。第一条真实错误原文：
  `FAIL: version literals 'jmeters' and '0.4.5' embedded`
  → `ERROR: jmeters/0.4.5@ohpcd/stable (test package): Error in test() method, line 55`
  → `ConanException: Error 1 while executing`
  根因（本包一手事实）：移植 archives/z/zita 检查器时替换了字面量却没同步 `memmem` 的 needle 长度
  （`"zita-rev1"`=9 字节 → `"jmeters"` 只有 7 字节），断言恒假；打包二进制里实测含
  `jmeters`×6、`0.4.5`×1，代码正确、检查器写错。已把长度改回 7。
- 第 2 次 `conan-verify`（round2-verify-r2.log）= **VERIFY_RC=0**，`reports/conan-verify-report.md` 判 PASS。
- 构建日志里的 `make: pkgconf: No such file or directory`（多处）来自上游
  `jmeters: CPPFLAGS += $(shell pkgconf --cflags freetype2)`，OHOS 侧 PATH 无 pkgconf；
  配方 generate() 已把依赖 include/lib 目录注入 CPPFLAGS/LDFLAGS，故 freetype2/Xft 头解析不依赖该探针，非致命。
- 运行时边界（如实划界，不当成功证据）：诊断性 `jmeters -h` 在本沙箱报
  `Error loading shared library libXft.so.2` 与 `Error relocating ... XftFontOpenName: symbol not found`
  等（musl loader 不认 LD_LIBRARY_PATH 下的用户目录，见 knowledge/graph/E088.kv:2），
  且设备无 X 显示服务与 JACK server。
  检查点 4 的口径是"DT_NEEDED 里每个 so 在 LD_LIBRARY_PATH 各目录下 `access(R_OK)` 命中"，
  属文件解析证据，**不是**"可加载/可运行"证据；本包只申报编译+打包+消费者静态断言通过，
  **不申报可运行**。

### conan-verify 报告逐字读数（`reports/` 不入库，故抄录于此）
`reports/conan-verify-report.md`（第 2 轮，PASS）：

```
3:**Verdict**: PASS
26:## G2: ✅ PASS
30:## G3: ✅ PASS
34:## G4: ✅ PASS
35:  ⚠️ 无法找到程序包 ID
37:## L2: ✅ PASS
38:  ⏭️ 跳过（无 cache 路径）
40:## L4: ✅ PASS
41:  ⏭️ 跳过（无 cache 路径）
43:## L5: ✅ PASS
44:  ⏭️ 跳过（无 cache 路径）
```

⇒ **G4 与 L2/L4/L5 不计为通过**：`G4` 带 `⚠️ 无法找到程序包 ID`；`L2/L4/L5` 三行的标题图标是框架初值，
正文三行原文均为 `⏭️ 跳过（无 cache 路径）`，即 smoke/安全/基线三项**未执行**。
本报告可作为通过证据的只有 `**Verdict**: PASS` + `G1/G2/G3`。

### W3 本地 CI 模拟（第 2 棒，B 机真机 2026-09-26 06:29，`finish jmeters 0.4.5 built`）

runner 判决行（`~/tmp/uc2/z64-jmeters/w3-r1.log`，逐字）：

```
65:  ✅   ✅ 本地 CI 模拟通过 (日志: /storage/Users/currentUser/qzy/主理-64-jmeters-0.4.5/archives/j/jmeters/0.4.5/reports/w3-local-ci.log)
66:  ✅   ✅ W3 本地 CI 模拟通过
```

被判决的日志件 `archives/j/jmeters/0.4.5/reports/w3-local-ci.log` 一手读数（该文件按规则不入 git）：

```
-rw-r----- 1 20001006 file_manager 85268 2026-09-26 06:29 archives/j/jmeters/0.4.5/reports/w3-local-ci.log
sha256sum  6c3fcb8909ea01c7cd2a02839579d25a9537e2c57d71db992ea83a10a39482ba
grep -c "\[step\]"   -> 48
grep -c "_RESULT="   -> 8
wc -c                -> 85268
```

门禁状态文件 `archives/j/jmeters/0.4.5/.ci-result.json`（同样不入库，全文逐字）：

```json
{
  "timestamp": "2026-09-26T06:29:38.836757",
  "exit_code": 0,
  "software": "jmeters",
  "version": "0.4.5",
  "step": "W3_local_ci",
  "archive_dir": "/storage/Users/currentUser/qzy/主理-64-jmeters-0.4.5/archives/j/jmeters/0.4.5",
  "integrity_hash": "2df6295549138e88",
  "log_sha256": "6c3fcb8909ea01c7cd2a02839579d25a9537e2c57d71db992ea83a10a39482ba"
}
```

互锁核对：`.ci-result.json` 的 `log_sha256` 与上面 `sha256sum` 实算值**逐字相同**
⇒ 状态文件绑定的是这份 W3 日志本身，未错位、未沿用旧件。

`finish` 整体 rc（同一 runner 日志）：

```
166:=== FINISH_RC=2
```

rc=2 的组成（逐字，**均为收尾/门禁外的步骤，不影响 W3 判决**）：

```
  ❌ 无法定位源码目录: orig=None, work=None
  ℹ️   ⚠️ 无编辑追踪器，使用排除规则扫描差异...
  ✅   无差异，保留现有补丁        ← Step 1 refresh-patch（见下方"知识引用"第 2 条）
  ❌ G0: 找不到原始 tarball        ← Step 3 G0 把未展开的 prefix 模板占位传给 configure
  ⚠️   gen_summary 失败: 'str' object has no attribute 'append'   ← Step 8
  ⚠️    失败步骤: step5b, step8
```

⇒ W3（Step 5）本身判 ✅，`exit_code=0`，故本包 W3 记为**通过**；`finish` 的 rc=2 由
Step1 的"无差异"文案、Step3 的 G0 取不到 tarball 与 Step8 的 gen_summary 崩溃构成，
已按框架既有读数记录在案（同族 zita/looktxt 的 finish 也是 rc=2 常态），**不据此重跑、不写成本包缺陷**。

### 对话 #1（第 1 棒 · 2026-09-26 06:0x，主理-64）
- 定源（官方直链 + 自算 sha256 + `-4` 可达性）、W0 逐依赖 `--only-recipe` 下载取证、按
  archives/z/zita/0.2.2 家族范式出首稿配方（10 文件 / +744 行，提交 `1bdd1b0c51`）。
- `conan-verify` 第 1 轮 G2 FAIL → 根因定位为移植检查器时 `memmem` needle 长度未随字面量改（→ 恒假），
  改回 7 后第 2 轮 VERIFY_RC=0；`refresh-patch` 因生成物名单吞掉被改过的 `source/Makefile`，
  改为手工构造 `.orig/.work` 两棵树 + 模块级 `edit_tracker.snapshot()` 建基线后由精准模式生成补丁。
- 未做（当时边界）：W3 / 知识草稿 / 对外文本。

### 对话 #2（第 2 棒 · 2026-09-26 06:2x-06:3x，主理-64）
- 跑 `gate.sh` + `build-slot.sh --kind short --mem 2500` + `finish jmeters 0.4.5 built`，
  取回 W3 判决三值与互锁（上节逐字）；核对 `finish` 回写的文件——仅本 `notes.md` 被追加收尾块，
  `manifest.yaml` / `conandata.yml` 的 diff 为空（`grep -c ghfast`=0、`grep -c mirrors`=0），
  未出现镜像前缀回写，也未出现删段。
- 复核第 1 棒给的全部行号证据（`refresh_patch.py:22,23-26,46,59-60,184-188,215,220-222,370,386,416,418,430-432,397`、
  `edit_tracker.py:73,256-280`、`init_build.py:337`）在 HEAD `1bdd1b0c51` 逐行成立；
  复验 `test_jmeters.c` 的 `memmem` needle 长度（:248 `"jmeters", 7`、:249 `"0.4.5", 5`，与字符串长度一致，恒假已消除）。
- 补齐"审查实测口径四式"中未跑的两式（`*RUNTEST*`、`src/demo|examples/*.c`）读数 → 均为 0，
  并据此把上游静态合计定为 0；补 `鸿蒙特有测试` 行（0 条 + 承担 OHOS 运行面判据的断言清单）。
- 落成对知识草稿 `knowledge/drafts/DRAFT-7646-refresh-patch-generated-names-makefile.{kv,md}`；
  补软件级 `archives/j/jmeters/manifest.yaml` 与 `README.md`（`finish` Step 6 曾报 `⚠️ 软件级缺失: README.md`）。

### 知识引用（对应 manifest.yaml 的 knowledge_gained 三条，逐字）
1. "裸 Makefile 的 kokkinizita/JACK GUI 家族配方范式已在 archives/z/zita/0.2.2 合入：去 -march=native、$(INSTALL) 参数化、CLTHREADS_NO_PTHREAD_CANCEL、依赖 include/lib 走 CPPFLAGS/LDFLAGS 注入、package 阶段 PREFIX=/、消费者测试用纯 C 四项静态断言——jmeters 直接复用同一范式"
2. "移植该检查器时必须同步 memmem 的 needle 长度：zita 的字面量是 9 字节、jmeters 只有 7 字节，长度不改会让断言恒假并在 G2 的 test() 才暴露"（→ 复验读数见「对话 #2」）
3. "上游 Makefile 的 $(shell pkgconf --cflags freetype2) 在 OHOS 无 pkgconf，只会打印 make: pkgconf: No such file or directory，不阻断构建（依赖头由 conan 注入）"

本 PR 新增的知识草稿（成对，同 stem）：`knowledge/drafts/DRAFT-7646-refresh-patch-generated-names-makefile.kv`
与 `.md` —— refresh-patch 的 `_GENERATED_NAMES` 名单（含 `Makefile`）在"已修改文件"分支也被分类，
导致改过的上游 Makefile 被判构建产物、静默丢弃并报"无差异，保留现有补丁"（rc=0）；
绕行办法是手工构造 `.orig/.work` 两棵树并调用模块级 `edit_tracker.snapshot()` 建基线，逼进不做分类的精准模式。

## 适配路径声明（3+2）
- **适配路径**：路径 B（贡献创新）——新增一条 refresh-patch 补丁生成静默丢改动的机制知识与绕行法，配方本身走已合入的 zita 家族范式
- **使用知识库**：复用 archives/z/zita/0.2.2 范式、knowledge/graph/E088.kv:2、knowledge/drafts/DRAFT-8958-clthreads-makefile-stage-install-shadow.md、knowledge/drafts/DRAFT-8543-refresh-patch-rename-conandata-desync.md；新增 DRAFT-7646-refresh-patch-generated-names-makefile（同 stem .md/.kv 成对）
- **知识库扩展**：DRAFT-7646-refresh-patch-generated-names-makefile —— `refresh_patch.py:215-222` 在 `diff_files` 分支复用"生成物名单"分类，被修改的 `Makefile` 被跳过 ⇒ 「无差异，保留现有补丁」+ rc=0
- **关联 Issue**：#3445（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3445）
---

**编译结束**: 2026-09-26 06:29
**状态**: built（W3 本地 CI 模拟通过，`.ci-result.json` exit_code=0；finish 整体 rc=2 的组成见上文 W3 节）

### 对话 #9（主理收口：finish 收尾块，由设备实算读数生成）
**最终状态**：built —— W3 本地 CI 模拟通过，证据与本块同源于该 worktree。
- 证据件：archives/j/jmeters/0.4.5/reports/w3-local-ci.log（mtime 2026-09-26 06:29 archives/j/jmeters/0.4.5/reports/w3-local-ci.log，85268 字节）
- 判决行计数：[step] 标记 48 条、*_RESULT= 判决 8 条（逐字抄录如下）
      - G0_RESULT=pass
      - KC_RESULT=pass
      - JC_RESULT=pass
      - L0_RESULT=pass: all checks passed
      - L1_RESULT=pass: test_package executed
      - L2_RESULT=skip: jmeters version/help failed
      - L4_RESULT=pass: patches clean
      - L5_RESULT=pass: bin/ has content
- 互锁：.ci-result.json 的 exit_code=0；其 log_sha256 前缀 6c3fcb8909ea01c7 与本 log 的 sha256sum 前缀 6c3fcb8909ea01c7 同串
- 口径：L2 若为 skip 属框架预期（CI 裸跑 bin 不经 runenv），不构成本包可执行证据；本包运行期证据以 test_package 实跑行为准
