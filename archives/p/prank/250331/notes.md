# prank 250331 适配笔记

## 编译环境
- 构建系统: makefile（上游只有一个手写的 `src/Makefile`，无 configure/cmake/meson 层）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++，`Target: aarch64-unknown-linux-ohos`（OHOS SDK）
- 机器: HarmonyOS PC（A 机，aarch64，真机构建，非交叉编译）
- 状态: built

## 编译步骤

工具链信息全部以 **make 命令行变量覆盖**注入（零补丁）——上游 Makefile 里这 8 个变量都是
普通赋值，命令行覆盖优先级高于文件内赋值，因此不需要动一行源码：

```bash
# 等价于 conanfile.py build() 实际执行的命令（<src> = <source_folder>/src）
make -j1 -C <src> \
  CC="<conf tools.build:compiler_executables:c>" \
  CXX="<conf tools.build:compiler_executables:cpp>" \
  LINK="<同 CXX>" \
  DEFINES=-DNDEBUG \
  CFLAGS="-O3 -DNDEBUG" \
  CXXFLAGS="-O3 -DNDEBUG" \
  INCPATH="-I." \
  LFLAGS= \
  prank
```

> 目标显式写成 `prank` 而不是默认目标：默认目标 `all: Makefile $(TARGET) $(MANPAGES)`
> 会用 `pod2man` 从 `prank.1.pod` 重生成 man 页（Makefile 第 34 行 POD2MAN、第 117/142 行）。
> 直接构建二进制目标可把 perl 摘出关键路径；man 页取上游快照自带的 `src/prank.1`。

`package()` 放置 `bin/prank` 与 `man/man1/prank.1`（上游 `install:`/`uninstall:` 是 FORCE 空规则，
`make install` 是静默空操作）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 起手即 `gcc: No such file or directory` | Makefile 第 7/8/13 行把 `CC=gcc`、`CXX=g++`、`LINK=g++` 硬编码，OHOS SDK 只提供 clang/clang++ | 从 Conan conf `tools.build:compiler_executables` 取绝对路径，以 `CC=/CXX=/LINK=` make 覆盖传入（R33：不读裸 `$CC`/`$CXX`） |
| 2 | 链接期 `clang: error: unsupported option '-m64'` | 第 10/11 行 `CFLAGS/CXXFLAGS = -m64 -pipe -O3`、第 14 行 `LFLAGS = -m64`，`-m64` 是 x86-64 专有旗标 | 按 `build_type` 重建为 `-O3 -DNDEBUG`，并把 `LFLAGS` 覆盖为空 |
| 3 | 头文件路径指向不存在的系统目录 | 第 12 行 `INCPATH = -I. -I/usr/include`，`/usr/include` 是**构建主机**的，不是 OHOS sysroot | 覆盖为 `INCPATH="-I."`——PRANK 全部头文件都相对 `src/` 包含 |
| 4 | `make install` 什么都没装 | 第 584/586 行 `install: FORCE` / `uninstall: FORCE` 是空规则，上游没有任何安装逻辑 | `package()` 自行 `copy()` 二进制与 man 页到包内 |
| 5 | 默认目标把 perl 拽进关键路径 | `all` 依赖 `$(MANPAGES)=prank.1`，规则体是 `pod2man` | 显式构建 `prank` 目标；man 页用快照自带的 `src/prank.1` |
| 6 | 并行编译诊断交错 | OHOS 的 make 包装不暴露 jobserver | `-j1`（实测 GNU Make 4.4.1，36 个 TU 单线程足够快） |
| 7 | 跑起来后 `mkdtemp` 失败 | PRANK 用 `mkdtemp(TMPDIR\|TMP\|TEMPDIR\|TEMP)` 建临时目录，OHOS 上 `/tmp` 只读 | 运行侧必须有可写 `TMPDIR`；test_package 把 `--work`/`--json` 指到 Conan 自己的 build 文件夹下，不依赖 `/tmp` |
| 8 | `prank -version` 非零退出 | 单横线 `-version` 不是"打印版本"，它真的向 `prank-msa.googlecode.com` 发 TCP 请求查更新，域已停 → `exit(1)` | 版本/用法一律走 `--version`（未知选项分支，打印 `prank v.250331` 后 `exit(0)`）或 `-help`；CI 的 L2 smoke 同口径 |
| 9 | G2 首跑 FAIL：`AttributeError: 'Requirement' object has no attribute 'name'` | test_package 用 `for ref, dep in self.dependencies.items()` 再取 `ref.name` 定位被测包；Conan 2.29 的 `items()` 键是 `Requirement` 对象且不再暴露 `.name`，`test()` 在跑任何断言之前就抛 | 改成仓库主流的直接名查表 `self.dependencies["prank"]`（`archives/a/abcde`、`aaudit` 等大量在库配方同一写法），取 `.package_folder` + `.cpp_info.bindirs` |

## 已试过的失败方案

| 方案 | 实测结果 | 结论 |
|------|----------|------|
| 取源用 SourceForge `https://downloads.sourceforge.net/project/prank/prank.source.250331.tgz` | `curl` 3 次全部 HTTP 404、154 字节、`tar tzf` BAD | 上游旧家已停，弃 |
| 取源用 `https://raw.githubusercontent.com/ariloytynoja/prank-msa/master/binaries/previous_version/prank.source.250331.tgz` | 5 次采样全部 `rc=7`（连接被拒）/`http=000` | 设备侧不可达，弃 |
| 取源用 GitHub 官方仓库址 `.../raw/refs/heads/master/binaries/previous_version/...` | 裸 curl 采样抖动（`rc=52` 空回复 / `rc=28` 90s 超时只收到 49152/158741 字节），但 `conan create` 经 E017 镜像注入路径 2 次全绿 | **采用**：它是上游自己文档（`docs/prank_installation.html`）给出的取源址，形态合法；抖动由框架的下载镜像注入 + 源码下载缓存吸收 |
| 取源用 Debian 池 `https://deb.debian.org/debian/pool/main/p/prank/prank_250331.orig.tar.gz` | 3/3 HTTP 200、158741 字节、sha256 与官方址**逐字节同值** `4847b565…113b9` | **不作取源**（下游重打包源，R39/PF7），只用作 sha256 的交叉核验 |
| `build()` 跑 `make check` 作为层 1 测试 | 干净树 `make -n check` 展开为 37 条命令行 = 36 编译 + 1 链接，**0 条测试命令**；`pod2man` 因 `prank.1` 已 up-to-date 未出现 | 零收益且会把 `$(MANPAGES)`/perl 拽回关键路径，弃 |
| 把 `grep -rn 'assert(\|FAIL\|EXPECT' src/*.cpp` 的命中当成"上游有测试" | 实测 61 命中：60 条 `assert(xa>0)` 维度前置条件调用集中在 boolmatrix.cpp/dbmatrix.cpp/flmatrix.cpp/intmatrix.cpp 4 个生产源文件（`grep -rc assert( src/*.cpp` 每文件 15 条）；而 `#include <cassert>` 的实际主语是同名 4 个**头文件** boolmatrix.h/dbmatrix.h/flmatrix.h/intmatrix.h（各 1 次，见 src/*.h:32；`grep -rln cassert src` 只命中这 4 个 .h、.cpp 内为 0），且构建带 `-DNDEBUG` 会编译掉，1 条是 `prank.cpp:78` 的 `exit(EXIT_FAILURE)`；`ASSERT_\|EXPECT_\|TEST(\|TEST_F(` 命中 **0** | 不是测试用例，层 1 仍为 0，据实写进 `test_package/MANIFEST.yml` |
| 放宽 `EXPECTED_ASSERTIONS` 或砍场景数以迁就首跑失败 | —— | **未采用**（缩分母是硬禁）；第 9 条是真 API 用错，改访问方式后 37/37 原样通过 |

## 源码修改

**零补丁**：`conandata.yml` 的 `patches: {}`，`patches/` 目录为空。OHOS 需要的全部改动都是
make 命令行变量覆盖（见上），未触碰上游任何源文件。

## 依赖版本

- 编译依赖：clang/clang++ 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）、GNU Make 4.4.1、
  Python 3.14.7、Conan 2.29.1（profile `ci/conan/profiles/ohos-aarch64`）。
- 精确 Conan 依赖：**无**（`preflight_check.sh` 与 conanfile 均无 requires）。
- PRANK 自带精简后的 Eigen 线性代数子集（`src/eigen.cpp`）与自家 Newick/矩阵解析器，不链外部库。
- 运行时外部可选程序 mafft / exonerate / bppancestor / raxmlHPC 只在对应命令行选项下被调用，
  默认 DNA/蛋白比对路径、指导树输出与格式转换都不依赖它们。
- 产物链接：`ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`——纯 musl 动态，
  无系统同名库冲突（G3 PASS）。

## 验证结果

### 五维测试口径

| 维度 | 数量 | 依据 |
|------|------|------|
| 上游静态声明的测试用例 | 0 | 干净解压树逐条清点（`test_package/MANIFEST.yml`）：无 test/tests 目录、无 `*test*` 文件、无样例语料、`add_test`/CTest 0 命中 |
| 上游注册/可执行的测试 | 0 | `make -n check` 展开 37 条命令行，测试命令 0 条 |
| 实测执行（上游 N_executed） | 0 | 上游无任何测试用例可执行（`make -n check` 展开 = 36 编译 + 1 链接、**0 条测试命令**），故上游口径实测执行 = 0；0 个用例不可能执行 37 次 |
| 消费者测试（N_consumer） | 1 个程序 / 37 条断言 | `test_package/msa_check.py` 单程序，`conan create` 内真跑，7 场景 × 退出码 + 输出双判 = 37 条消费者断言（属消费者口径，不并入上游 N_executed） |
| 跳过 | 0 | 本机即 OHOS 真机，非交叉构建，`can_run()` 为真 |
| 失败 | 0 | `MSA_CHECK_RESULT=… "failed": 0` |

消费者测试（test_package）：N_consumer = **1** 个程序（`test_package/msa_check.py`），断言数 **37**（7 场景 × 退出码 + 输出双判）；上游实测执行 = 0（见上五维表）。

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游快照 77 个文件里无任何测试程序 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | `make check` 只重编整个程序，0 条测试命令 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 0 | 上游无单元可测，不虚构分母 |
| 集成测试 | 0 | 0 | 同上 |
| 鸿蒙特有测试 | 37 | +37 | 消费者测试（test_package/msa_check.py）：以使用者身份跑**打包后的** prank，7 场景 37 条断言，每条同时判退出码与产物内容 |
| **合计** | **37** | +37 | |

### 机器可读判决行（唯一证据锚 = sha 锁定的 `reports/w3-local-ci.log`）

权威锚点是 `reports/w3-local-ci.log`（实算 `sha256=9c9c009bc1054228d4dd65eb3cc96cac3ba91f665d6c1d5283332c1aec96e1c4`，与 `.ci-result.json.log_sha256` 逐字相同）；下列行号为整改时逐条 `grep -n` 复验所得：

```
# 真编译证据（build()/package() 均实跑，见下方 :170/:181）：
$ grep -n "Calling build()" reports/w3-local-ci.log
188:prank/250331: Calling build()
$ grep -n "Calling package()" reports/w3-local-ci.log
1273:prank/250331: Calling package()
$ grep -n MSA_CHECK_RESULT reports/w3-local-ci.log
1345:MSA_CHECK_RESULT={"binary": "…/p/b/prankdb4393cb37f47/p/bin/prank", "discovered": 37, "executed": 37,
       "failed": 0, "framework": "consumer-msa-harness", "passed": 37, "skipped": 0}
$ grep -n HMBS_TEST_PACKAGE_RESULT reports/w3-local-ci.log
1347:HMBS_TEST_PACKAGE_RESULT={"binary": "…/p/b/prankdb4393cb37f47/p/bin/prank",
       "command": "python3 msa_check.py --prank <pkg>/bin/prank", "discovered": 37, "executed": true,
       "failed": 0, "passed": true, "passedCount": 37, …}
$ grep -n "consumer MSA harness: 37/37 assertions passed" reports/w3-local-ci.log
1348:prank/250331 (test package): consumer MSA harness: 37/37 assertions passed
```

被测对象是**包内**二进制（`…/home-z68-prank/p/b/prankdb4393cb37f47/p/bin/prank`，W3 真编译落盘的包目录），不是构建树里的临时产物。

`- Cache` / `Already installed!` 两族行为什么**不算**“build() 未跑”的反证：`w3-local-ci.log:167` 的 `- Cache` 属**配方取用**阶段（`Computing dependency graph` 里 `prank/250331#5f1b681f…` recipe 命中），紧接 `:170` 即印 `prank/250331: Forced build from source`、`:181` `Building from source` ⇒ 二进制并非取自缓存而是真编；`:1287`/`:1291` 的 `- Cache` 与 `:1294` 的 `Already installed! (1 of 1)` 则是 `Calling package()`(:1273) **之后**、test_package **消费者依赖安装**阶段对被测包的解析（属另一主体，非配方 build()）。判“真编译”的唯一锚是 `Calling build()`/`Calling package()` 计数（本日志各 1 次），而非“日志里出没出现过 Cache 字样”。

旁证（不作 build/package/判决锚）：`reports/conan-create.log` 现仅 131 行、是其后一次缓存命中（G2 复跑）的单轮日志（`:62`/`:77` 均为 `Already installed!`、`Calling build` 计数 0、判决行包目录为缓存命中的 `prankad89bbcaee8f3`）——它印证同一批断言 37/37，但⛔ 不再被当作 build()/package()/判决的行号来源。

### conan-verify 八道门禁（2026-09-26 16:45 CST，A 机真机，缓存已清白的干净构建）

```
G0 预构建风险评估     PASS（构建系统判定 unknown，非阻塞）
G1 配方完整性         PASS
G2 conan create      PASS   ← 首跑 16:30 FAIL（第 9 条问题），修 test_package 后 16:34 / 16:45 两次 PASS
G3 系统同名库隔离 R26 PASS
G4 产物完整性         PASS
L2 平台功能 smoke     PASS
L4 静态安全扫描       PASS
L5 产物基线对比       PASS
Verdict: PASS（工具提示"可标记 status→published"；本包未 upload ⇒ manifest/本笔记按实际记 built）
```

### 运行时抽查

```bash
$ TMPDIR=<可写目录> <pkg>/bin/prank --version
Unknown option: --version

prank v.250331. …            # 版本横幅与 250331 一致，退出码 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/prank` | 924160 B | ELF 64-bit LSB arm64，dynamic `/lib/ld-musl-aarch64.so.1`，`-O3 -DNDEBUG` |
| `man/man1/prank.1` | 7782 B | 上游快照自带的已渲染 man 页（不经 pod2man 重生成） |

## 注意事项

1. **调用方必须给可写 `TMPDIR`**：OHOS `/tmp` 只读，PRANK 的 `mkdtemp` 会直接失败。
2. **别用 `-version` 做健康检查**：它会联网查更新并 `exit(1)`；用 `--version` 或 `-help`。
3. 版本串 `250331` 与上游一致（一手证据 `src/prank.cpp:41  version = 250331;`），未做"归一化"。
4. 取源 URL 是上游官方仓库内的发布件，Debian 池址只作 sha256 交叉核验、不作取源。
5. `reports/` 被仓库 `.gitignore` 忽略，`reports/w3-local-ci.log` 与 `.ci-result.json` 默认不入 git；
   W3 三一致核对要在设备侧本地做（见 manifest.yaml 的 evidence_marker）。
6. `commands.json` 的 `binary` 目前为 `false`，上传制品仓后应改 `true`。
---

**编译结束**: 2026-09-26 16:50
**最终状态**: built


## 路径与知识声明（与 PR 正文逐字同源）
- **适配路径**：路径 A（基础适配）＋ 知识库扩展（本 PR 携带 1 条新增条目，见下两行与「补充说明」）
- **使用知识库**：本 worktree 根 `SKILL.md` 及其路由的 `KNOW_YOUR_WHY.md` / `CONTRIBUTING.md` / `docs/TEST_QUALITY_SPEC.md` / `knowledge/ARCHIVE-SPEC.md`；`python3 scripts/ohc-run.py recipe-search prank` 只回**本包自身骨架**（top1 = `archives/p/prank/250331/conanfile.py`，score=0.5）⇒ catalog 内无第三方同族底稿，首稿按检索到的既有处方写；命中并复用的条目（每条先读原文标题与处方再采纳）：`E392`（裸 Makefile 的 Conan 三陷阱：`tools.build:compiler_executables` 是**字典**、必须 `check_type=dict` 整体取用；`self.run("make …")` 要显式 cwd——本包据此从 conf 取 clang/clang++ 绝对路径并以 make 命令行变量覆盖，⛔ 读裸 `$CC/$CXX`，即 R33）；`E017`（GitHub 源在 CI/本地预下载阶段会被**就地改写**成代理镜像优先，且会污染活文件 `conandata.yml`——日志自称"已还原"不等于还原成功 ⇒ 收口必须 `git diff` 核对 URL 回到官方标量。该条目原名指向 `ghfast`，而当前框架对 GitHub 域注入的是 `gh-proxy`，本包实测取源抖动由这条注入路径 + 源码下载缓存吸收）；`E499` 已读并**判定不适用**（它讲的是共享依赖的运行期 libdirs 传递，本包 `requires` 为空、产物纯静态链接，症状不同形）。
- **知识库扩展**：新增 1 条 = `knowledge/drafts/DRAFT-prank-250331-conan2-requirement-has-no-name-attr.{kv,md}`（同 PR 成对提交）。机制：Conan 2.29.1 的 `Requirement` 类不再暴露 `name` 属性（A 机零构建实测 `hasattr(r,"name")` = `False`，包名在 `ref.name` / `pkg_name` 下），而 `self.dependencies` 是以 `Requirement` 为键的映射 ⇒ "遍历 `dependencies.items()` 再用循环键取 `.name` 定位被测包"这种写法会在 `test()` 跑**任何断言之前**抛 `AttributeError`，把 G2 打成与配方、依赖、被测二进制全都无关的红；正解是按包名直查 `self.dependencies["prank"]`（本仓 `archives/a/abcde`、`archives/a/aaudit` 等同形），被测引用仍按 §9 优先用 `self.tested_reference_str`。
- **关联 Issue**：#3467（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3467）
