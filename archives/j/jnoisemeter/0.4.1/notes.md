# jnoisemeter 0.4.1 适配笔记

## 编译环境
- 构建系统: makefile（上游只有 `source/Makefile`，无 configure、无 CMake、无 meson）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15（由 Conan profile `ci/conan/profiles/ohos-aarch64` 的
  `tools.build:compiler_executables` 指定，os=OHOS / arch=armv8 / libc++）
- 状态: built（第 1 棒：取源 + 配方 + conan-verify + 首稿提交；第 2 棒：W3 本地 CI 模拟
  **已通过**，判决与读数逐字见「W3 本地 CI 模拟（第 2 棒）」小节；第 3 棒：W5 独立审计
  第 1 轮三条 P1 的整改，见「第 3 棒整改」一节 —— **W3 复跑未执行**（设备门槛 `gate.sh`
  连红，原文读数在该节），故本文件的 W3 证据仍是第 2 棒的、且**先于** P1-3 的
  `test_package` 改动；未发布、未建 PR）

## 编译步骤

1. `ohc-run.py recipe-search jnoisemeter` → 语料 6173 条**无相似配方**，首稿走模板。
2. `bash ci/scripts/preflight_check.sh jnoisemeter/0.4.1` → 因 conanfile 尚未生成，
   只报「无依赖需要检查」（不构成 W0 证据），依赖发布态改由第 3 步判定。
3. **W0 依赖判定**：
   `conan install --requires=clxclient/3.9.2 --requires=jack/1.9.22 --build=never`
   （profile ohos-aarch64）→ 全闭包逐个 `Retrieving package ... from remote 'ohpcd'` +
   `Package installed` + `Downloaded package revision`，末行 `Install finished successfully`，
   rc=0 ⇒ 依赖全部已发布，无需 block、无需先适配依赖。
4. `init-build` 下载官方 tarball 并解包（见「注意事项」第 1 条：框架把嵌套 `source/` 提升）。
5. `conan-init` 生成的骨架按上游真实形态重写（模板误判为 autotools/library，
   实际是 makefile/application）。
6. 修改 `source/Makefile` 四处可移植性 → `track-edit add` + `refresh-patch --auto`
   生成 `patches/0001-source-Makefile.patch`。
7. 编译：
   `make -C source -j1 CXX=<profile clang++> PCONFCFL="<各依赖 includedirs + OHOS 宏>" LDFLAGS="<各依赖 libdirs>" jnoisemeter`
8. 打包：`make -C source install PREFIX=/ DESTDIR=<package>` ⇒ `<package>/bin/jnoisemeter`（55808 字节）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游硬写 `CXXFLAGS += -march=native` | clang 15 在 AArch64 不支持 `-march=native`；且按构建机调优的二进制不得进包 | 补丁删除该行，代码生成完全交给 profile 指定的工具链（R33） |
| 2 | `CPPFLAGS += $(shell pkgconf --cflags freetype2)` 探宿主 pkg-config | CI/交叉环境不应依赖宿主 pkg-config 状态；FreeType 头在 Conan 包里 | 补丁把该行替换为 `$(PCONFCFL)` 槽位，include 由配方从依赖包注入 |
| 3 | 直接在 make 命令行覆盖 CPPFLAGS 会丢 `-DVERSION` | make 命令行变量优先级最高，会吃掉 makefile 内的 `+=`；而 `VERSION` 被 `mainwin.cc:55` 与 `jnoisemeter.cc:50` 引用 | 不覆盖 CPPFLAGS，改为补丁新增 `$(PCONFCFL)` 追加槽位（aliki 0.3.0 同样以补丁造槽位；clxclient 的上游自带该名） |
| 4 | OHOS PATH 上没有裸 `install` | 无 coreutils，只有 toybox | 补丁引入 `INSTALL ?= /bin/install` 并把 install 目标两行改为 `$(INSTALL)` |
| 5 | 上游 Makefile 无 `PCONFCFL` 槽位（同族里 clxclient 上游自带、aliki 与本包一样靠补丁造） | 该包 Makefile 更朴素 | 不假设同族模板一致：先读 `source/Makefile` 再改，用补丁造槽位而不是猜变量名 |

## 源码修改

`patches/0001-source-Makefile.patch`（+4/-4，纯可移植性，不含 `#ifdef __OHOS__` 平台宏）：

- `CPPFLAGS += $(shell pkgconf --cflags freetype2)` → `CPPFLAGS += $(PCONFCFL)`
- `CXXFLAGS += -march=native` → `INSTALL ?= /bin/install`
- `install -d $(DESTDIR)$(BINDIR)` → `$(INSTALL) -d $(DESTDIR)$(BINDIR)`
- `install -m 755 jnoisemeter $(DESTDIR)$(BINDIR)` → `$(INSTALL) -m 755 jnoisemeter $(DESTDIR)$(BINDIR)`

未改动任何 `.cc/.h`。`PREFIX ?=` / `BINDIR ?=` 与链接行 `$(CXX)` 上游本已可用，无需再改。

## 依赖版本

- 直接依赖：clxclient/3.9.2、clthreads/2.4.0、libxft/2.3.8、libx11/1.8.13、
  xorgproto/2025.1、jack/1.9.22
- 由上述包传递闭包带入并同样已在 ohpcd 发布：freetype/2.14.3、fontconfig/2.18.3、
  libxrender/0.9.12、libxcb/1.17.0、libxau/1.0.11、libxdmcp/1.1.5、libxml2/2.15.3
- 证据：`conan download <ref> -r=ohpcd --only-recipe` 九个引用全部落到本地缓存
  （带 revision 与时间戳），且 `conan install --build=never` 全闭包 rc=0

## 上游测试账本

| 维度 | 读数 |
|------|------|
| 分母（上游测试总数） | **0**：`source/Makefile` 只有 `jnoisemeter` / `install` / `uninstall` / `clean` 四个目标；tarball 内只有 AUTHORS、COPYING、README、docs/（filters.pdf、oct1band.png）与 source/，无 tests/ 目录、无 ctest/pytest/autotools 测试注册 |
| 实测 | `cd source && make check` → `make: *** No rule to make target 'check'.  Stop.`（一手证据，非推断） |
| 已运行 / 通过 | 0 / 0（无可运行项，未以任何 `--disable-*` 缩减分母） |
| 不可运行原因 | 不适用：上游本就没有测试，不是"跑不了" |
| 替代覆盖（test_package） | 2 例 3 断言，见下节，全部真跑并 PASS |

## 验证结果

```bash
# ── 轮次 R1（第 1 棒，06:05 前后）：conan-verify 独立跑，三一致 PASS
#   （三一致 = 文字 PASS + 报告 Verdict 行 PASS + rc=0）
python3 scripts/ohc-run.py conan-verify jnoisemeter 0.4.1
#   G1 PASS / G0 PASS / G2 PASS(conan create 成功) / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
#   ✅ 配方验证通过: jnoisemeter 0.4.1      OUTER_VERIFY_RC=0
#   R1 的报告件 reports/conan-verify-report.md 该轮判决行原文: **Verdict**: PASS
#   （reports/ 被仓库根 .gitignore:96 忽略、**不随 PR**，所以判决行抄在这里而不是给行号；
#    同一件在 R2 复审轮被就地覆写成 **Verdict**: FAIL —— 两读并存的完整披露与定性见
#    「conan-verify 的两种 Verdict（按轮次披露）」节，本文件不再留裸行号引用）

# ── 轮次 R1：G2 内 conan create 自动执行 test_package（真跑，非跳过）
#   该轮日志 RUN 行逐字抄录（其中的 .../ 是该轮日志自带的缩写，不是本文件的省略）:
#     RUN: LD_LIBRARY_PATH=".../runtime-libs" ".../test_jnoisemeter.sh" ".../p/bin"
#   同轮输出行逐字: JNOISEMETER_SMOKE_PASS banner=1 nodisplay_exit=1
#   ⚠ 该 RUN 行里的 runtime-libs 地址已由第 3 棒 P1-3 改址（改法见「第 3 棒整改」节）；
#     新 staging 的**实际绝对路径**要在 W3 复跑后回填，本棒未复跑 ⇒ 暂缺，不作声称。

# ── 轮次 R1：对已打包并 ELF 签名的产物单独复跑（独立取证）
LD_LIBRARY_PATH=<该轮 runtime staging 目录> sh test_package/test_jnoisemeter.sh <package/bin>
#   （R1 当时该目录 = <test_package>/runtime-libs；第 3 棒起改址，见上条 ⚠）
#   同轮输出逐字: JNOISEMETER_SMOKE_PASS banner=1 nodisplay_exit=1   rc=0
<package/bin>/jnoisemeter -h        -> 横幅 "jnoisemeter-0.4.1"（stderr），exit 1
env -u DISPLAY -u XAUTHORITY <package/bin>/jnoisemeter -> "Can't open display."，exit 1（不是 127）
#   ⇒ 完整共享库闭包（clthreads/clxclient/jack/Xft/X11）在 OHOS 上真的解析成功
```

说明：`-h` 与"无 DISPLAY"两条路径都在 `main()` 打开 X display 之前/之处返回，
因此可在无显示、无 JACK server 的 CI 上执行；`exit 1` 是上游 `help()` 的正常路径，
`!= 127` 才是本用例要断言的加载器证据。上游无 `--version`/`--help` 长选项。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/j/jnoisemeter/commands.json` | R38 命令声明（单命令 jnoisemeter，type=tool） |
| `0.4.1/conanfile.py` | makefile 型 application 配方，141 行 |
| `0.4.1/conandata.yml` | 官方源 url + 自算 sha256 全串 + portability 补丁声明 |
| `0.4.1/patches/0001-source-Makefile.patch` | +4/-4 可移植性补丁 |
| `knowledge/drafts/DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot.kv`（仓库根） | 路径 B 草稿（机器可读），同 stem `.md` 成对 |
| `knowledge/drafts/DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot.md`（仓库根） | 路径 B 草稿（人读），含 `make -n` 三组对照实测读数 |
| `archives/j/jnoisemeter/manifest.yaml` | 软件级 manifest（本轮补齐 finalize 告警的缺失项） |
| `archives/j/jnoisemeter/README.md` | 软件级 README（同上） |
| `0.4.1/test_package/` | conanfile.py（OHOS 运行时闭包 staging + ELF 签名）+ test_jnoisemeter.sh + MANIFEST.yml |
| `0.4.1/reports/` | **不入库**（`.gitignore:96` `reports/`）：conan-verify-report.md、conan-create.log、w3-local-ci.log；判决已逐字抄进本文件 |
| `0.4.1/.ci-result.json` | **不入库**（`.gitignore:238`）：W3 三值，全文已抄进本文件 |
| `<package>/bin/jnoisemeter` | 55808 字节 ELF64/AArch64，已签名 |

## 注意事项

1. **框架 `init-build` 的「嵌套源码提升」与官方包布局不一致**：它把 `jnoisemeter-0.4.1/source/`
   展平进 `.orig`/`.work` 顶层，而 conan 侧 `strip_root=True` 拿到的真实布局是
   `source/Makefile`。按展平布局生成的补丁路径是 `a/Makefile`，在 conan 里命中不了。
   本轮按真实布局重建 `.orig`/`.work` 后重跑 `track-edit` + `refresh-patch --auto`，
   才得到 `a/source/Makefile` 形式的正确补丁。**同族的其它包若照此路走都要注意。**
2. **`init-build` 在 `check_env()` 处崩溃**：`scripts/ohc/check_env.py:32-33` 的
   `except Exception:` 缺 `as e`，走异常分支时 `str(e)` 抛 `NameError: name 'e' is not defined`；
   触发条件是 `~/usr/local/bin/automake` 的 shebang 指向不存在的 `~/usr/local/bin/perl`
   （本机 perl 在 `/data/service/hnp/bin/perl`），execve 以 ENOENT 失败。崩溃发生在
   download/解包/骨架生成之后、写 `.build-context` 之前，导致 `refresh-patch` 定位不到源码目录。
   本轮未重跑 `init-build`（避免覆盖已手写的配方），改为手工补写
   `.build-context-jnoisemeter-0.4.1` 后继续。**框架缺陷本身不在本 PR 修（W2/框架改动需单独 PR）。**
3. jnoisemeter 是 X11 GUI 应用，同时是 JACK 客户端，运行需要显示服务器与 jackd；
   OHOS/CI 无这些设施，运行时测试以「加载完整闭包并到达正常提前退出路径」为通过标准。
4. conan-verify 的 G4/L2/L4/L5 在本轮报告里是 `⚠️ 无法找到程序包 ID` + `⏭️ 跳过（无 cache 路径）`
   却仍记 `✅ PASS`——真正的可执行证据来自 G2 内 `conan create` 自动跑的 test_package，
   不来自这四个图标（见「验证结果」节 R1 组抄录的 RUN 行与横幅输出）。
5. conandata.yml 的 `sources.url` 为官方源，无任何镜像前缀（R39）；sha256 为本机自算全串
   `e20c39b18c378c51e2ac951c0f2fd9fdf2e0137a852246c8a18e3975eb71effe`（64 位），
   与台账前缀 `e20c39b18c378c51e2ac951c0f2fd9` 一致；官方址 `curl -sI` 返回 HTTP/1.1 200 OK、
   Content-Length 120965，实测下载字节数与之相符。
6. `reports/` 与 `.ci-result.json` 均被仓库根 `.gitignore` 命中（`:96` 的 `reports/`、
   `:238` 的 `.ci-result.json`），**不随 PR 入库** ⇒ W3 的判决与逐项读数在本文件
   「W3 本地 CI 模拟（第 2 棒）」小节里**逐字留档**，读者只靠 notes 即可复核。
7. 本轮**未**执行独立审计（W4）、未 submit/上传制品、未建 PR；
   manifest.yaml 的 status 因此如实写 `built`，不写 `published`。

## 路径与知识声明

- **适配路径**：路径 B（贡献创新）——新增一条可跨库复用的机制：上游裸 Makefile
  没有任何"可追加"的 include 落点时，自造一个"只被引用、从未被赋值"的变量当
  Conan cflags 的注入通道（本包实证变量名 `PCONFCFL`）。
- **使用知识库**：复用 `knowledge/graph/E478.kv:22,34,36`（conan-verify 点号版本号
  → package ID 解析失败，G4/L2/L4/L5 跳过）、`knowledge/graph/E466.kv:22,36`
  （`init-build` 的 `_promote_nested_source` 只按 C/C++ 构建标记判断嵌套源码）、
  `knowledge/graph/E312.kv`、`knowledge/graph/E313.kv`（`/usr/bin/install` 缺失族）、
  `knowledge/drafts/DRAFT-8958-clthreads-makefile-stage-install-shadow.kv:92,98`
  （裸 `install` → `INSTALL=/bin/install` 的 forbid_2、`CXXFLAGS += -march=native`
  的 forbid_3）、`archives/a/aliki/0.3.0/notes.md:33 与 archives/a/aliki/0.3.0/patches/0001-source-Makefile.patch:14
  （安装工具写成 make 变量时"命令行变量优先于 makefile 内赋值"的把手）；
  新增 `knowledge/drafts/DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot.kv`（改址：与本仓 1942 件既有草稿同目录；原置于归档内 `0.4.1/knowledge/drafts/` 的形状不被出厂门禁识别，CIW-7 已 git mv 到仓库根）
  与同 stem `.md`（成对随本 PR 提交）。
- **知识库扩展**：`DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot`——把上游
  `CPPFLAGS += $(shell pkgconf --cflags freetype2)` 的右值换成 `$(PCONFCFL)`
  （全文件不出现任何 `PCONFCFL` 赋值），配方在命令行给它赋值注入 `-I`，
  既保住上游 `CPPFLAGS += -MMD -MP -DVERSION=\"$(VERSION)\"`，又彻底摆脱宿主 pkgconf。
- **关联 Issue**：#3443（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3443）。

## W3 本地 CI 模拟（第 2 棒，2026-09-26 06:17–06:19）

过闸与择槽（一手读数）：

```
$ sh ~/tmp/uc2/gate.sh
GATE_PASS:probe=clang MemAvailable=6727MB MemFree=883MB Cached=9638MB swap余=47594MB inode余=? load=20.400 20.263 20.302 PSI_full=avg10=69.97 编译器进程=0 RSS=0MB
$ sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 --wait 1800 -- python3 scripts/ohc-run.py finish jnoisemeter 0.4.1 built
SLOT_OK 06:17:06 cmd=python3 scripts/ohc-run.py finish jnoisemeter 0.4.1 built
```

W3 判决（**逐字**抄自 runner stdout；`✅ W3 本地 CI 模拟通过` 只印在 runner 里，
不在 `reports/w3-local-ci.log` 内。runner 全文存 `~/tmp/uc2/z64-jnoisemeter/w3-r1.log`，
11370 字节（同样是**不随 PR** 的本机文件，故 ✅ 行已逐字抄在下方代码块），
起手工牌 `HEAD=c2255c5f57cb51b66836d1a4cba1fa773a039f42`）：

```
  ℹ️ Step 5/10: 本地 CI 模拟 (W3) [阻塞门禁]...
  ℹ️ W3: 本地 CI 模拟验证 (jnoisemeter/0.4.1), 超时预算 3600s ...
  ℹ️   [1/2] setup.sh...
  ✅   ✅ setup.sh 通过
  ℹ️   [2/2] build_and_test.sh jnoisemeter/0.4.1...
  ✅   ✅ 本地 CI 模拟通过 (日志: /storage/Users/currentUser/qzy/主理-64-jnoisemeter-0.4.1/archives/j/jnoisemeter/0.4.1/reports/w3-local-ci.log)
  ✅   ✅ W3 本地 CI 模拟通过
```

机器可读三值（`archives/j/jnoisemeter/0.4.1/.ci-result.json` 全文，未跟踪件）：

```json
{
  "timestamp": "2026-09-26T06:19:17.115099",
  "exit_code": 0,
  "software": "jnoisemeter",
  "version": "0.4.1",
  "step": "W3_local_ci",
  "archive_dir": "/storage/Users/currentUser/qzy/主理-64-jnoisemeter-0.4.1/archives/j/jnoisemeter/0.4.1",
  "integrity_hash": "696d9f0053655ef8",
  "log_sha256": "823357c47d34fb5eeee2a283e264b3831df911a304ffe64a8a6f9197c685b2f0"
}
```

`log_sha256` 与实算一致（同一条 `sha256sum` 读数）：

```
$ sha256sum archives/j/jnoisemeter/0.4.1/reports/w3-local-ci.log
823357c47d34fb5eeee2a283e264b3831df911a304ffe64a8a6f9197c685b2f0  archives/j/jnoisemeter/0.4.1/reports/w3-local-ci.log
$ wc -c < 同一文件           → 79736      （mtime 2026-09-26 06:19）
$ grep -cF "[step]"   同一文件 → 48
$ grep -cF "_RESULT=" 同一文件 → 8
```

`reports/w3-local-ci.log`（R2 轮产物）的逐项判决与 `[step]` 计数：**判决行本身逐字抄在下面**，
读者只靠本文件即可复核。该日志件被 `.gitignore:96` 忽略、不随 PR —— 本文件按「抄原文 +
声明载体不入库」处理，不用 `git add -f` 把 79KB 日志塞进 PR；下面的 `N:` 前缀只是抄录时的
定位注记，不构成读者可复核的引用：

```
23:G0_RESULT=pass
70:KC_RESULT=pass
97:JC_RESULT=pass
817:L0_RESULT=pass: all checks passed
818:L1_RESULT=pass: test_package executed
819:L2_RESULT=skip: jnoisemeter version/help failed
820:L4_RESULT=pass: patches clean
821:L5_RESULT=pass: bin/ has content
```

末段（逐字）：

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on jnoisemeter
[step] L2: Smoke test (version/help check)...
[warn] L2: jnoisemeter --version/--help failed (non-blocking)
[step] Generating ci-metadata.json...
[ok] ci-metadata.json written

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
[step] Pre-download: conandata.yml 已还原为官方 URL
```

`L2_RESULT=skip` / `[warn] L2` 的原因是上游无 `--version`/`--help` 长选项
（日志自身标注 non-blocking），**按 skip 记录，不计入通过**；测试账本仍以
"上游静态分母 0 + 适配后 test_package 2 例 / 3 断言真跑" 为准（见上两节），
W3 侧的对应证据是 `L1_RESULT=pass: test_package executed` 与 L1e 的破坏性反证。

## `finish` 同轮并存的其它步骤读数（第 2 棒 06:17 轮；框架侧，不参与本包定性）

`python3 scripts/ohc-run.py finish` 是多步流水线，本轮整体收尾打印
`⚠️ 编译收尾部分完成: jnoisemeter 0.4.1 → failed`、`失败步骤: step3, step5b, step8`；
逐步并存读数如下（同窗四个包同现象，均非 jnoisemeter 自身的构建缺陷）：

- **step3 G0 干净构建验证**：`❌ G0: configure 失败 (exit 127)` —— 框架把未展开的
  prefix 模板占位当成 configure 命令传给 shell（127 = command not found），
  本包是 makefile 型、根本没有 `configure` 脚本。
- **step4/5b 内嵌 conan-verify**：`G1: PASS`、`G2: ❌ FAIL`，
  `ERROR: jnoisemeter/0.4.1@ohpcd/stable (test package): Error in test() method, line 46`
  `PermissionError: [Errno 13] Permission denied: '.../tmp/ch/home-jnoisemeter-64/p/b/jnoise6cf1ba07a536/p/bin/jnoisemeter'`，
  知识图谱按 E077（ELF 签名后权限）给建议。并存事实：第 1 棒独立跑
  `ohc-run.py conan-verify jnoisemeter 0.4.1` 为 G1..L5 三一致 PASS；本轮 W3 内
  同一条 test_package 路径 `L1_RESULT=pass: test_package executed`（见上）。
  ⇒ 本小节只登记两次读数不一致这一现象，不定性为本包缺陷，也未据此重跑构建。
    **两种 Verdict 的逐字读数、一手 traceback 与定性集中写在
    「conan-verify 的两种 Verdict（按轮次披露）」节**，不在此处重复。
- **step6 finalize-archive** 告警：`软件级缺失: README.md`、`缺少 release/debug tar.gz`、
  `notes.md 无对话记录`。前两项中 README.md 与软件级 manifest.yaml 本轮已补齐，
  tar.gz 属 submit/发布阶段产物（本轮不发布，如实缺）；`无对话记录` 由本轮补入
  「### 对话 #1 / #2」两节。
- **step8 SUMMARY**：`gen_summary 失败: 'str' object has no attribute 'append'`（框架侧）。
- **step9 W2 原子性**：`✅ 仅含配方变更 (9 文件)，无框架文件`。
- **step10 submit 就绪预检**（未执行 submit，仅登记）：缺 `reports/test-report.md`、
  `packaging/`、`.staging-verified` 三项。
- `refresh-patch` 被 step1 内部重跑一次：`patches/0001-source-Makefile.patch`
  **字节未变**（`git diff` 不含该文件，仍 +4/-4，work hash 由 `ae8bb54c2aad4786`
  记为 `faf29c692a11ef8a` 只是重算时间戳/顺序所致），`conandata.yml` 未被回写
  镜像前缀（`grep -c ghfast` = 0、`grep -c mirrors` = 0）。

## conan-verify 的两种 Verdict（按轮次披露：R1 第 1 棒 = PASS，R2 第 2 棒复审轮 = FAIL）

同一个报告件 `0.4.1/reports/conan-verify-report.md` 被两轮执行**就地覆写**，读者拿到的是
最后一轮的字节，而 `reports/` 不随 PR ⇒ 两读在此按轮次各自留档，不混写。

- **R1（第 1 棒，独立 `python3 scripts/ohc-run.py conan-verify jnoisemeter 0.4.1`）= PASS**
  三一致逐字读数（同「验证结果」节 R1 组）：
  `G1 PASS / G0 PASS / G2 PASS(conan create 成功) / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS`、
  `✅ 配方验证通过: jnoisemeter 0.4.1`、`OUTER_VERIFY_RC=0`、报告判决行 `**Verdict**: PASS`。
- **R2（第 2 棒 06:17:42–06:17:44，`finish` step4/5b 内嵌 conan-verify，即"复审轮"）= FAIL**
  该轮报告判决行 `**Verdict**: FAIL`；一手错误两行逐字（该轮 `conan-create.log` 第 409-414 行
  traceback 的末两行，件不随 PR，故抄于此）：
  ```
  ERROR: jnoisemeter/0.4.1@ohpcd/stable (test package): Error in test() method, line 46
  PermissionError: [Errno 13] Permission denied: '/storage/Users/currentUser/tmp/ch/home-jnoisemeter-64/p/b/jnoise6cf1ba07a536/p/bin/jnoisemeter'
  ```
  traceback 末帧（审计件复述）：`_sign_ohos_elf` 第 153 行
  `os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o755)` 抛 EACCES。
  ⇒ 行号随第 3 棒的 P1-3 修改而位移，**上述行号对应基线提交 `100df712cc` 的 `test_package/conanfile.py`**。

**定性（主理已定，本棒直接引用、未重做）：R2 的 FAIL 是"复审轮对同一 test_package 的重复执行
副作用"，不是产物不可执行。** 四条一手支撑：

1. 异常抛在 `os.chmod`，**不在 `exec`**；被 chmod 的对象 `p/bin/jnoisemeter` 是首次 create
   已签名的缓存包（mtime 06:05、mode `-rwxr-x---`、55808 字节、ELF 头 `7f 45 4c 46`，现仍在盘）。
2. 同一轮日志 06:17:42–44 有 **13 条 `add codesign section success`** ⇒ 签名链路当时在正常跑。
3. 06:19 的 W3 换用**新建包目录** `p/b/jnoise250a8c0185e8b` 跑同一条 test_package，逐字输出
   `JNOISEMETER_SMOKE_PASS banner=1 nodisplay_exit=1`（该轮 `.ci_logs/conan_build_jnoisemeter_0.4.1.log:693-694`，
   件不随 PR），W3 侧对应判决行 `L1_RESULT=pass: test_package executed` ⇒ 产物真可执行。
4. 知识图谱按 E077（ELF 签名后权限）给建议，属框架把 create 失败一律映射到签名知识；
   框架侧问题不在本 PR 修（见「注意事项」第 2 条的同一口径）。

⇒ 对外口径：本包的 verify 证据以 **R1 三一致 PASS + R2 W3 的 `L1_RESULT=pass`** 为准；
R2 的 `Verdict: FAIL` 按上述定性登记为"重复执行副作用"，两种读数都摆在这里、各自标轮次。


## 第 3 棒整改（W5 独立审计第 1 轮 P1×3，基线 `100df712cc`）

审计判决件：`~/tmp/uc2/z64-jnoisemeter/audit-r1.md`（6630 字节，md5
`bfa01786a343772b5b5ebcffdd48c893`，**P0=0 P1=3 P2=3**）。

### P1-3（面 11）：test_package 运行期 staging 移出归档目录、每轮唯一

一手缺陷：`test_package/conanfile.py:40` 把 staging 定在 `build_folder/runtime-libs`，
绝对路径落在 **PR 归档目录内**
（`archives/j/jnoisemeter/0.4.1/test_package/runtime-libs`，两处独立证据：该轮
`.ci_logs/conan_build_jnoisemeter_0.4.1.log:693` 与该轮 `reports/conan-create.log:181`；这两件都不随 PR，故另给一条只靠 git 就能自证的：`git show --stat cd382c927f` 列出的正是 `archives/j/jnoisemeter/0.4.1/test_package/runtime-libs/` 下那 114 枚 `.so`，撤销它的提交是 `100df712cc`）；
`_prepare_ohos_runtime` 在该基线态的 `:71/:76/:77` 对这**同一固定目录**
`shutil.rmtree` + `mkdir(exist_ok=False)`、无每轮唯一后缀 ⇒ 框架 L1e 对同一 test_package
起**第二次** `conan test` 会同目录互覆。实拍后果：114 枚 `.so` 曾被按目录 `git add` 卷进
提交 `cd382c927f`，由主理以 `100df712cc` 撤销。

本轮改法（**只动 `test_package/conanfile.py`**，未动 `conanfile.py`/`conandata.yml`/补丁）：

- 新增 `_staging_base()`：依次取 `TMPDIR`/`TMP`/`TEMP`（须为已存在目录），否则回退
  `$HOME/tmp`（本项目的可丢弃产物区）；**没有任何回落到包目录的分支**。
- 新增 `_new_runtime_staging_dir()`：路径
  `<staging 根>/jnoisemeter-runtime-<pid>-<uuid4 前 12 位>`，`mkdir(parents=True,
  exist_ok=False)` —— **每轮新建、永不复用**；`OSError` 直接转 `ConanException`
  （建不出来 ⇒ 构建红，不静默兜底）；建好后显式 `os.chmod(mode | 0o755)`，
  **不用 `mktemp -d`**（hmdfs 会把 0700 改写成对 euid 不可写）；末尾自证解析后的
  staging 路径不等于、也不落在 `self.recipe_folder` 之内，落在内即抛错。
- `_prepare_ohos_runtime()` 去掉 `rmtree` + `mkdir(exist_ok=False)` 这个"固定目录二次
  运行必炸/互覆"的形状，改为"目录由本轮唯一新建 ⇒ 目录不在就是错，抛 `ConanException`"。
- 自证读数（本棒实测）：改后文件 11952 字节、`ast.parse` 通过；
  全文已无 `build_folder, "runtime-libs"`（False）、无 `shutil.rmtree(root)`（False）。

### P1-2（面 13）：`knowledge_gained` 三条补可解析 ref

`ohc-run.py check-knowledge-gap jnoisemeter 0.4.1` 在基线 `100df712cc` 报
`manifest.yaml: knowledge_count=3 unreferenced=3`。框架判据（`scripts/ohc/check_knowledge_gap.py:63-66`）
是"以 `- ` 开头的条目行内出现 `knowledge_ref` / `ref:` / `reference:` 之一"⇒ ref 必须与条目**同行**，
写成下一行的 `ref:` 不认。按仓内已合并形状（同窗 vcdimager 2.0.1 的
`...；knowledge_ref: archives/v/vcdimager/2.0.1/notes.md:69`）给三条各补
`knowledge_ref: archives/j/jnoisemeter/0.4.1/notes.md:<行>`，行号指向**本文件里的真实动作行**
（改动前后各自 `sed -n` 复核，见本小节末）。

### P1-1（面 12）：行号证据改成随 PR 可复核的载体

缺陷：原判据/实测读数**全锚在被 `.gitignore:96`（`reports/`）与 `:238`
（`.ci-result.json`）忽略的文件上**，`git ls-files` 内 reports 件 = 0 ⇒ PR 读者读不到；
并且基线 `notes.md:80` 引 `reports/conan-create.log:712`，而该件已被第 2 棒 06:17 复审轮
就地覆写成 **414 行** ⇒ 悬空行号。

本轮改法（三处，均"抄原文 + 声明载体不入库"，⛔ 不 `-f` 日志件）：

1. 「验证结果」节按 **R1/R2 轮次分组**重写，把 `conan-verify` 判决行、`test_package` 的
   RUN 行与 `JNOISEMETER_SMOKE_PASS` 输出行**逐字抄进 notes**，删掉
   `reports/conan-create.log:712` 这一悬空引用（「注意事项」第 4 条同步改指本文件内）。
2. 新增「conan-verify 的两种 Verdict（按轮次披露）」节：PASS 与 FAIL 两读并列、
   节标题带轮次，附 R2 的错误两行原文与四条定性支撑。
3. W3 那块的措辞改成"判决行逐字抄在下面、`N:` 前缀只是抄录定位注记、不构成可复核引用"；
   `finish` 读数小节的标题补轮次（`（第 2 棒 06:17 轮；框架侧…）`）。
   runner 日志（`~/tmp/uc2/z64-jnoisemeter/w3-r1.log`）与 `.ci_logs/**` 同样声明为不随 PR。

### W3 复跑状态：**未复跑**（设备门槛 `gate.sh` 连红 4 次，本棒按规矩停手）

`sh ~/tmp/uc2/gate.sh` 四次实测原文（B 机，2026-09-26 07:3x）：

```
GATE_FAIL:MemAvailable=5354MB < 6000MB（可用内存不足，fork 可能失败）| MemAvailable=5354MB MemFree=867MB Cached=8073MB swap余=47408MB inode余=26405470 load=21.000 20.720 20.678 PSI_full=avg10=74.95
GATE_FAIL:MemAvailable=5379MB < 6000MB（可用内存不足，fork 可能失败）| MemAvailable=5379MB MemFree=888MB Cached=8073MB swap余=47437MB inode余=? load=20.333 20.566 20.652 PSI_full=avg10=74.86
GATE_FAIL:MemAvailable=5405MB < 6000MB（可用内存不足，fork 可能失败）| MemAvailable=5405MB MemFree=1048MB Cached=7911MB swap余=47429MB inode余=? load=20.300 20.520 20.611 PSI_full=avg10=74.89
GATE_FAIL:MemAvailable=5405MB < 6000MB（可用内存不足，fork 可能失败）| MemAvailable=5405MB MemFree=1047MB Cached=7911MB swap余=47429MB inode余=? load=20.300 20.520 20.611 PSI_full=avg10=74.88
```

旁证：`build-slot.sh --status` = 「本机长杆 0/2 · 机动 1/3（总 5 槽）」⇒ 槽位是空的，
压的是**槽外的内存占用**（load 20+ / PSI full avg10 74），不是本包太重；门槛差
595MB（5405 vs 6000）。**未做任何"这单轻所以可以跑"的自行放行**。

⇒ 由此产生的、必须写清的证据缺口：

- 本文件里唯一的 W3 证据仍是**第 2 棒 06:19** 那一组（`exit_code=0` /
  `step=W3_local_ci` / `log_sha256=823357c47d34fb5eeee2a283e264b3831df911a304ffe64a8a6f9197c685b2f0`）。
- 那一组日志由 **P1-3 修改前**的 `test_package/conanfile.py` 产出。改 `test_package/**`
  不改 recipe revision，但按门禁口径 **W3 必须重跑**才能把对外文本挂到新一轮读数上，
  也要靠新日志取 P1-3 的 staging 实际绝对路径自证。⇒ **本节不给"W3 已通过"的当前性背书。**
- 下一步（交回主理/第 4 棒）：等 gate 放行后
  `sh ~/tmp/uc2/gate.sh` → `sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 --wait 1800 --
  python3 scripts/ohc-run.py finish jnoisemeter 0.4.1 built`，runner stdout 落
  `~/tmp/uc2/z64-jnoisemeter/w3-r2.log`；再回填「验证结果」节那条 ⚠ 的 staging 绝对路径、
  新 `.ci-result.json` 三值与 `log_sha256`/`[step]`/`_RESULT=`/`wc -c`/mtime。

## 对话记录

### 对话 #1（第 1 棒：取源 → 配方 → conan-verify → 首稿提交）

- 已完成：官方 tarball 取源（sha256 全串见「注意事项」第 5 条）、W0 依赖判定
  （`conan install --build=never` 全闭包 rc=0）、`conanfile.py` 按 makefile 型
  application 重写、`patches/0001-source-Makefile.patch`（+4/-4 可移植性）、
  `test_package` 2 例 / 3 断言真跑、`conan-verify` G1/G0/G2/G3/G4/L2/L4/L5 三一致 PASS。
- 交回判据：首稿提交 `c2255c5f57cb51b66836d1a4cba1fa773a039f42`
  （== `git ls-remote origin refs/heads/feat/jnoisemeter-0.4.1`）。
- 登记的框架缺陷（不在本 PR 修）：`scripts/ohc/check_env.py:32-33` 缺 `as e`、
  `~/usr/local/bin/automake` 的 perl 绝对 shebang 悬空、`init-build` 嵌套源码提升
  与官方包布局不符（补丁路径 `a/Makefile` vs `a/source/Makefile`）。

### 对话 #2（第 2 棒：W3 → B 草稿 → 对外文本）

- 已完成：W3 本地 CI 模拟通过（三值 `exit_code=0` / `step=W3_local_ci` /
  `log_sha256` 与实算一致）；新增 B 草稿成对件
  `knowledge/drafts/DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot.{kv,md}`
  （含 `make -n` 三组对照实测读数）；补软件级 `archives/j/jnoisemeter/README.md`
  与 `archives/j/jnoisemeter/manifest.yaml`；版本级 `manifest.yaml` 的
  `knowledge_gained` 填入本条草稿、`patch_classification` 由 step1 重跑写入的
  `type: auto / guard: pending` 改回 `portability / always`；notes 补「路径与知识
  声明」「W3」「对话 #1/#2」三节。
- 已代做（主理）：Issue #3443 已建、knowledge_ref 已回填；W4 独立审计由主理派棒、
  PR/CI/提审等平台写操作、`reports/test-report.md` 与 `packaging/` 等 submit 前置。
- 未复核项：本轮未重跑 `init-build` / 未重写配方，第 1 棒交回的四条判据按已核事实引用。

### 对话 #3（第 3 棒：W5 审计第 1 轮 P1×3 整改）

- 已完成：P1-3（`test_package/conanfile.py` 的 runtime staging 移出归档目录 + 每轮唯一，
  去掉 `rmtree`+`mkdir(exist_ok=False)` 的固定目录形状）；P1-2（版本级 `manifest.yaml`
  三条 `knowledge_gained` 各补同行 `knowledge_ref` 指向本文件真实动作行，
  `check-knowledge-gap` 复跑 `unreferenced=0`）；P1-1（对外文本的行号证据改为随 PR
  可复核的载体：逐字抄录 + 轮次披露 + 删悬空引用）。
- **未做（卡点）**：W3 复跑 —— 设备门槛 `gate.sh` 连红 4 次（原文见「第 3 棒整改」节末），
  按"GATE_RC≠0 一律停手"未越闸；因此 P1-3 的 staging 实际绝对路径与新一轮三值仍缺，
  本文件的 W3 证据不具当前性。
- 未做（按分工交回主理）：Issue 创建与回填、W4 第 2 轮审计、PR/CI/提审等平台写操作、
  `reports/test-report.md` 与 `packaging/` 等 submit 前置。
---

**编译结束**: 2026-09-26 08:00
**最终状态**: built

## 第 4 轮补录（主理窗自取：新 W3 已于 08:02 通过，前一节"不背书"声明到此关闭）

- 触发：第 3 棒因设备内存门连红 4 次未能复跑 W3（`GATE_FAIL:MemAvailable=5354MB < 6000MB`，日志存 `~/tmp/uc2/z64-jnoisemeter/gate-r3*.txt`）。主理窗改按**退避重试**（10 次 × 75 秒，⛔ 未改门槛数值、⛔ 未绕闸），第 7 次拿到 `GATE_PASS:MemAvailable=6071MB`，随即 `build-slot.sh --kind short --mem 2500` 取槽执行 `ohc-run.py finish jnoisemeter 0.4.1 built`。
- 一手读数（`reports/w3-local-ci.log`，78986 字节，mtime 2026-09-26 08:02）：`sha256sum` = `51e4829b14f5bc4d3335693658d193568010fbe6e811c27cd0612c81e66c02fe`；`[step]` 计数 48、`_RESULT=` 计数 8。`.ci-result.json`：`exit_code: 0`、`step: "W3_local_ci"`、`timestamp: 2026-09-26T08:02:04.046002`、`log_sha256` 与上值**逐字相同**（互锁，非只比 mtime）。runner 日志 `~/tmp/uc2/z64-jnoisemeter/w3-r2.log:129` 印「✅ W3 本地 CI 模拟通过」；同轮 `:173` 仍报「失败步骤: step3, step5b, step8」（框架侧归因见前节，⛔ 读成本包构建失败）。
- **P1-3（staging 出归档 + 每轮唯一）的生效证据由本轮 W3 自证**：`reports/w3-local-ci.log:565` 原文
  `jnoisemeter/0.4.1 (test package): JNOISEMETER_TEST_RUNTIME_PATH=/storage/Users/currentUser/tmp/jnoisemeter-runtime-28620-b636fd310b42`
  ⇒ 落点在 `$HOME/tmp` 下、带 `<pid>-<uuid 前 12 位>` 的每轮唯一目录，**不在 PR 归档目录内**。核对：本轮跑完后 `find archives/j/jnoisemeter/0.4.1 -name "*.so*" | wc -l` = **0**；此前遗留在 `test_package/runtime-libs/` 的 114 枚运行期 `.so` 已整体移出到 `~/tmp/uc2/z64-jnoisemeter/runtime-libs-heldout-041`（未删除，属可再生产物，用户资产）。
- 知识面：`ohc-run.py check-knowledge-gap jnoisemeter 0.4.1` 在本 HEAD 复跑读数 `manifest.yaml: knowledge_count=3 unreferenced=0` + `✅ 知识完整性检查通过`（`notes.md: total=0` 按框架规则非缺陷）。
- 关闭声明：上一节末句「本节不给 W3 已通过当前性背书」**自本条起失效**——W3 已在包含 P1-3 修复后的 `test_package/conanfile.py` 的同一 HEAD 链上复跑并通过；本包对外文本里的 W3 数字一律以本条为准（前文出现的 06:19 那轮读数属修复前，仅作历史轨迹保留）。

## 第 5 节：上游测试四式的一手复算读数（由第 2 轮独立审计复算，主理照录，⛔ 冒充本窗实跑）

- 取源可核性：`~/tmp/uc2/z64-jnoisemeter/` 与 `~/tmp/builds/` 两处 tarball 的 `sha256sum` 均与 `conandata.yml` 声明的 `e20c39b18c378c51e2ac951c0f2fd9fdf2e0137a852246c8a18e3975eb71effe` **逐字符相同** ⇒ 被清点的那棵树就是本配方取源的那棵树。
- `tar tjf` 全清单穷举（审计读数）：只有 `README`、`source/`（26 个 `.cc`/`.h` + `Makefile`）、`docs/`（`filters.pdf`、`oct1band.png`）、`COPYING`、`AUTHORS` ⇒ 按 §12.72 四式逐项落零：
  1. `test*` 框架源码：`0`
  2. `res` 语料条目：`0`（`docs/` 下两张图与一份 pdf 属随包资源，不计入测试语料）
  3. `*RUNTEST*` 脚本：`0`
  4. `demo|examples` 下 `*.c`：`0`
- 与既有申报的一致性：`source/Makefile` 全文 52 行、目标仅 `jnoisemeter`(:35)/`install`(:41)/`uninstall`(:46)/`clean`(:50)，`make check` 原文 `make: *** No rule to make target 'check'.  Stop.` ⇒ **上游静态合计 0** 成立，且是"清单穷举 + 目标清点"双路一致，不是"跑不动所以记 0"。
- 口径变更说明：第 1 轮审计曾把这条记为**未取到 + 替代一手**（当时只用了补丁 `@@` 上下文换算），第 2 轮已否证该说法并取到一手 ⇒ 本 notes 自此以本节为准，前文若仍有"未取到"字样属历史轨迹。

### 对话 #9（主理收口：finish 收尾块，由设备实算读数生成）
**最终状态**：built —— W3 本地 CI 模拟通过，证据与本块同源于该 worktree。
- 证据件：archives/j/jnoisemeter/0.4.1/reports/w3-local-ci.log（mtime 2026-09-26 08:02 archives/j/jnoisemeter/0.4.1/reports/w3-local-ci.log，78986 字节）
- 判决行计数：[step] 标记 48 条、*_RESULT= 判决 8 条（逐字抄录如下）
      - G0_RESULT=pass
      - KC_RESULT=pass
      - JC_RESULT=pass
      - L0_RESULT=pass: all checks passed
      - L1_RESULT=pass: test_package executed
      - L2_RESULT=skip: jnoisemeter version/help failed
      - L4_RESULT=pass: patches clean
      - L5_RESULT=pass: bin/ has content
- 互锁：.ci-result.json 的 exit_code=0；其 log_sha256 前缀 51e4829b14f5bc4d 与本 log 的 sha256sum 前缀 51e4829b14f5bc4d 同串
- 口径：L2 若为 skip 属框架预期（CI 裸跑 bin 不经 runenv），不构成本包可执行证据；本包运行期证据以 test_package 实跑行为准

## 09-26 审查 P2 整改（CIW-7）

AI 复审（10:48 那轮，P0/P1 均 0、阻塞 0、建议 1）给出两条 P2，本窗两条都落：

1. `test_package/test_jnoisemeter.sh` 只有 `set -u`，缺 `-e` 与 `-o pipefail`，且第 23 行直接取 `$1`。
   这不是风格问题：少 `-e` 时脚本任何一步失败都会继续跑到最后一行打印
   `JNOISEMETER_SMOKE_PASS ... / exit 0` ⇒ 是一个**假通过面**。
   改为 `set -euo pipefail` 并按建议加 `[ $# -ne 1 ]` 用法守卫（`exit 2`，替掉
   `set -u` 抛出的 `unbound variable` 文法错）。
   ⚠ 严格模式必须同时把两处**故意失败**的上游行为显式 guard 掉，否则会把正常判成失败：
   - 上游 `help()` 打完横幅就 `exit(1)`，原先 `"$BIN" -h | grep -q` 在 `pipefail` 下**恒为失败**
     （管道状态取右端非零段）⇒ 改成先把输出捕获进 `banner`（`|| true`），再用 `case` 判文本；
     顺带去掉 `| head`（pipefail 下 `head` 提前关闭会让 `printf` 收到 SIGPIPE）。
   - 无 DISPLAY 裸跑期望返回 1 ⇒ 原 `cmd; rc=$?` 在 `-e` 下会直接中断，改成 `rc=0; cmd || rc=$?`。
   断言数与判据**未变**：`MANIFEST.yml` 的 `test_case_count: 2 / assertion_count: 3` 与正文两张表
   都不需改数（新增的是参数校验守卫，不构成对软件包的断言）。
   本地未做行为复跑：手搭 `LD_LIBRARY_PATH` 与 conan 的真实 runenv 不等价
   （`test_package/conanfile.py:41-56` 会把依赖 .so 暂存进 `runtime_root` 并先 `_sign_ohos_elf` 签名，
   且本机该 conan home 内根本没有 `libXft.so.2` 的实体）⇒ 借别的 conan home 的 .so 拼路径会造出
   "本地全绿"的假验证，故本窗只做 `/bin/sh -n` 语法检查（通过）+ 行为验证交给 CI 的真实 runenv。
2. `conandata.yml` 的 patches 项未显式声明 `patch_strip`。已补 `patch_strip: 1`，并注明依据：
   补丁头是 `--- a/source/Makefile`，而 `apply_conandata_patches()`（配方 `conanfile.py:80`）默认也是 1
   ⇒ **零行为变更的显式化**，不改 recipe 的有效输入。
