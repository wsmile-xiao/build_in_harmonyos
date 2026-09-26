# xininfo 0.14.11 适配笔记（HarmonyOS PC / aarch64）

- 上游：https://github.com/DaveDavenport/xininfo （单 C 文件 X11 多显示器查询工具，裸 GNU Makefile）
- 取源：官方 GitHub tag archive `refs/tags/0.14.11.tar.gz`，sha256 `53a9fc4df54d36fd2640c7a65f90c345ed7306e24d3a3a27629b12fb858aed5b`
- 构建机：B 机（HarmonyOS aarch64），CONAN_HOME=`~/tmp/ch/home-xininfo`，profile `ci/conan/profiles/ohos-aarch64`
- 结果：W3 本地 CI 模拟通过（L0/L1/L4/L5=pass，L2=skip 见下），消费者断言 6/6

## 0. 知识库声明（3+2）

- **适配路径**：路径 A（Conan 配方 + 上游 Makefile 变量覆盖，未改上游源码，patches/ 为空）
- **使用知识库**：E077（ELF `.codesign` 自签四步）、E355（conan 制品 `.pc` prefix 修正族）、
  `knowledge/drafts/DRAFT-E2186-autotools-deps-missing-dep-flags.kv`（`:26` title，见 §4.3）、
  `knowledge/drafts/DRAFT-ccfits-2.7-stale-pc-prefix-regen.kv`（`:26` title / `:37` affected_scope，见 §4.4）
  （以上在池草稿按文件名引用）；`knowledge/graph/E355.kv:38/:39` 为 `.pc` prefix 修正族的正式条目。
  **并按行号级并排补引三枚在池条目**（上一版把这一面记成"零命中"，其探针词只用了 `md2man`；
  改按机制特征词宽口径复扫 `knowledge/`（含 `knowledge/drafts/`）后被否证 ⇒ 引用面补全如下，
  三条都是**同机制参数化差异、不构成层次差**，故 B 判定维持 `hit`：不新建草稿、不建 Issue、不占本 PR 知识位）：
  - `knowledge/drafts/DRAFT-diction-1.11-runtime-data-relocatable.kv:15`
    「autotools 包把运行时数据目录（SHAREDIR=--prefix/share）在 configure 阶段烧进二进制：安装到其它前缀后
    默认查找失败，需改为 exe 相对查找并保留编译期回退」；其 `.md:30`
    「配方侧配合：`generate()`/`build()` 中 `--prefix={self.package_folder}`，使回退路径与安装布局一致」，
    `.md:40` 自陈同类模式在 autotools 包中常见。
    ≡ 本包 `conanfile.py:190-197`（注释即写"PREFIX 决定编译期烧进二进制的 MANPAGE_PATH（Makefile L25/L33）"）
    与 `:226`（`PREFIX` 作为 make 命令行变量指向 package_folder），实测读数
    `reports/w3-local-ci.log:238`。对齐后的参数化差异：条目是 configure 阶段 + `SHAREDIR`，
    本包是 make 命令行变量 + `MANPAGE_PATH`（裸 Makefile 没有 configure 可用）⇒ **同机制**。
  - `knowledge/drafts/DRAFT-11103-teseq-mdate-sh-iso-date-vti.kv:35`
    「makeinfo；OHOS 无 texinfo，make install 以 Error 127 失败。」
    ≡ 本包 §4.5：设备 PATH 无 `md2man-roff`（`Makefile:86` 的 manpage 规则要用它）⇒ 上游 `make install`
    （`Makefile:96`）不可用，配方绕开它自行 `copy()`（`conanfile.py:239-249`）。
    参数化差异：makeinfo/texinfo 对 md2man-roff，Error 127 对 command -v MISSING ⇒ **同机制**。
  - `knowledge/drafts/DRAFT-ldns-tools-1.9.2-split-boundary-is-install-target.kv:24`
    root_cause 末段「而聚合 `make install` 会连带 install-manpages」。
    ≡ 本包 `Makefile:96` 的 `install: $(INSTALL_PROGRAM) $(INSTALL_MANPAGE)` 正是同一聚合形态，
    手册页一支 `:92-94` → `:86` 在设备上必然失败 ⇒ 本包不按 install 目标安装手册页。**同机制**。
  - **残余增量（环境读数，不是机制 ⇒ 不立条目、不占本 PR 知识位）**：设备 PATH 同时缺 `install(1)`，
    使 `Makefile:90`/`:94` 两条 `install -Dm 755` 也无法执行 ⇒ 配方用 python `copy()` 代替
    （§4.5、`conanfile.py:239-249`）。建议由主理并入 `DRAFT-diction-1.11` 与 `DRAFT-11103-teseq`
    的 affected_scope；本子代理不改他人池中草稿。
- **知识库扩展**：本 PR 不新增草稿条目（主机制已被既有条目覆盖，判 hit；判定权在主理）
- **关联 Issue**：无（未建 Issue）

## 1. 上游测试清点（R51 三步法·第一步）

`find -type f` 官方 tag archive 全树 = **6 个文件**：`.gitignore LICENSE Makefile doc/xininfo.1 doc/xininfo.markdown source/xininfo.c`。

> **口径限定**：上面的"全树 6 文件"指**上游官方 tag archive 解包后的文件集合**（本轮 `tar xzf` + `find -type f` 复算：`.gitignore`、`LICENSE`、`Makefile`、`doc/xininfo.1`、`doc/xininfo.markdown`、`source/xininfo.c`），**不含**本仓归档目录里的配方件（`conanfile.py``conandata.yml`、两级 `manifest.yaml`、`notes.md`、`test_package/*`、`reports/*`）；本包归档目录 `archives/x/xininfo/**` 实测**无** `.edit-tracker.json`/`.tarball-sha256` 之类的工具件（`find archives/x/xininfo -name .edit-tracker.json -o -name .tarball-sha256` → 空）。"上游 6 文件"与本 PR 跟踪的 13 个文件是两个不同的数，不得互推。

- 无 `tests/`、`test/`、`t/` 目录，无任何测试源文件
- `grep -n "TEST\|check" Makefile` → **无输出**（115 行 Makefile 的目标只有 all(L66)/install(L96)/clean(L98)/indent(L103)/dist(L106)）
- 上游 GitHub 无 Release（`/releases/latest` → 404），仅 1 个 tag `0.14.11`（commit `36b69ca4c8b56adc1572a82a0167931cda30754b`）

⇒ **上游注册用例数 = 0**（不是"未跑"，是"不存在"）。

## 2. 测试账本（rule4：正文声明数 ≤ 实测数）

| 口径 | 数量 | 依据 |
|---|---|---|
| 上游静态用例数 | 0 | 上文清点（6 文件 / Makefile 无 TESTS·check） |
| 上游注册数 | 0 | 无 check/test 目标可枚举 |
| 上游实跑 pass/fail/skip | 0/0/0 | 无可跑对象；`HMBS_UPSTREAM_TEST_RESULT.status=no_tests` |
| 消费者（test_package）断言数 | **6** | 声明值 `EXPECTED=6`（`test_package/test_xininfo.sh:35`）；`discovered` 不再是常量，而由 `ok()`/`bad()` 各自增一次 `checked` 后赋值（`:39-40`、`:145`），收尾对 `checked != EXPECTED` 判失败（`:148`）⇒ 整段分支被跳过时不可能被记成 6/6 |
| 消费者实跑 pass/fail/skip | **6/0/0** | W3 日志 `reports/w3-local-ci.log:334 assertions_declared=6 assertions_executed=6`、`:335 discovered=6 passed=6 failed=0` |

W3 日志原文（`reports/w3-local-ci.log`，**24448 字节 / 369 行**，md5 `9dfd088aa24cdd82705b5e64758681ab`，sha256 `65b5406c578cebea3cf27d32fbd18a30c2208d233fa3083784f9dbf1755a6aac`，与 `.ci-result.json` 的 `log_sha256` 逐字相等、`exit_code: 0`、`step: W3_local_ci`。本 notes 引用的随 PR 证据件只有两件：`reports/w3-local-ci.log`、`reports/conan-create.log`（`git add -f`）；框架件 `reports/conan-verify-report.md` 已从提交面移出，见 §6.6。本轮因 `test_package/test_xininfo.sh` 改动导致 recipe revision 变，已重跑 conan-verify → finish → graph validate，**以下行号是按重跑后的新日志重锚的**：G0=`:23`、KC=`:67`、L0i/L0j/L0k/L0m=`:31-40`、JC_RESULT=`:94`、镜像改写=`:97`/`:100`、依赖 `- Cache`=`:174-180`、烧录 PREFIX=`:238`、make 命令行注入=`:243`、conan test RUN 行=`:326`、A1–A6 与两行计数=`:327-336`、`conan create passed`=`:341`、L0/L1/L2/L4/L5=`:355-359`、Success:/Pass rate:=`:365`/`:367`）：

```
# 以下逐字摘录自随 PR 的 reports/w3-local-ci.log 的 :327-336、:355-359、:94（非连续，行号见上）
[OK]   A1 packaged binary is an AArch64 ELF executable
[OK]   A2 .codesign section present in the packaged ELF (E077 self-signature shipped)
[OK]   A3 '-h' reaches help() and hits the deterministic execlp(man) failure path (rc=0)
[OK]   A4 no-X error path reached through the real libX11 (rc=1, 'cannot open display!')
[OK]   A5 libX11/libXrandr/libXinerama are DT_NEEDED and XOpenDisplay/XRRGetScreenResources/XineramaIsActive resolve inside that closure
[note] LD_BIND_NOW=1 run also reached the no-X path (corroboration only, not counted)
[OK]   A6 man page installed at share/man/man1/xininfo.1 (non-empty, titles xininfo)
assertions_declared=6 assertions_executed=6
discovered=6 passed=6 failed=0
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xininfo.sh","discovered":6,"passedCount":6}
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: xininfo version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
JC_RESULT=pass
```

## 3. 功能测试为何不可执行（一手原因，不编造）

xininfo 是 X11 客户端，**运行时必须有 X server**。B 机实测（2026-09-25，命令与结果原文）：

| 探针 | 读数 |
|---|---|
| `echo "DISPLAY=[$DISPLAY]"` | `DISPLAY=[]`（空） |
| `command -v Xvfb / Xephyr / Xwayland / xxdpyinfo` | 全部 MISSING |
| `command -v man` | MISSING |
| `command -v md2man-roff / pandoc / install` | 全部 MISSING |
| `command -v pkg-config / clang / make / bash / readelf / nm / binary-sign-tool / llvm-objcopy` | 全部在 `/data/service/hnp/bin` |

同仓先例口径一致：`archives/c/clipnotify/1.0.2/test_package/test_nox.sh`（无 X 确定性错误路径断言）、
`archives/x/xsel/1.2.1/test_package/test_xsel.sh`（--version/--help + 无 X 优雅失败）。
⇒ 本包不发明新的降级形态，按先例把断言面收敛到"可执行 + 签名同源 + 上游确定性错误代码路径 + 链接/符号可用性 + 产物完整性"，
并在 A4 里**真实调用 libX11 的 XOpenDisplay**（rc=1 + `cannot open display!`，源码 L369-374），不是空壳。

佐证（不计入断言）：A5 之后另跑了一次 `LD_BIND_NOW=1`，同样命中 no-X 路径；因无法证明本机加载器确实启用即时绑定，故不作为断言计数。

## 4. 症状 → 根因 → 方案（三轮 W3 实拍）

### 4.1 `make: *** No rule to make target .../obj/source/xininfo.o` 型失败：clang 写不出 .o

- 症状（第 1 轮 G2 日志原文）：
  `error: unable to open output file '.../b/build-release/obj/source/xininfo.o': 'No such file or directory'`
- 根因：配方在 build() 里先 `os.makedirs(obj_dir)` 预建了 `BUILD_DIR`，导致上游 Makefile L68-73 的
  `$(BUILD_DIR): mkdir -p $@ ; mkdir -p $@/$(SOURCE_DIR)` 规则因目标已存在而被 make 跳过 ⇒ `obj/source/` 从未建立。
- 最小复现：`make all BUILD_DIR=<已存在的空目录>`（日志里不会出现 `Creating build dir`）。
- 已试过的失败方案：在配方里自己 `makedirs(obj_dir/source)` —— 等于把上游规则重写一遍，放弃。
- 最终方案：**不预建目录**，交给 Makefile L68-73 自建（第 2 轮日志出现 `Creating build dir` 即生效）。
- 适用边界：所有"用命令行变量把上游 out-of-tree 目录指走"的裸 Makefile 包。

### 4.2 `make: --cflags: No such file or directory`（×2）

- 根因：上游 Makefile L53 是 `PKG_CONFIG?=$(shell which pkg-config)`，L58/L59 直接 `${PKG_CONFIG} --cflags/--libs`；
  在 conan 的 build 环境里该展开取不到命令（同一次 make 里 L42 的 `$(shell which clang)` 却成功打印
  `Using clang compiler: /data/service/hnp/bin/clang`），于是 `--cflags` 被当成命令执行。
  探针证据：`conanbuildenv-release-armv8.sh` 只导出 `PKG_CONFIG_PATH`，**不导出 PKG_CONFIG**；
  而在 conanbuild 环境里 `which pkg-config` → `/data/service/hnp/bin/pkg-config` 正常。
  ⇒ 结论：这是 `?=` 形态在该环境下的求值问题，未继续深挖（不定性为平台缺陷）。
- 最终方案：配方用 `shutil.which("pkg-config")`（回落 `/data/service/hnp/bin/pkg-config`）定位后，
  **以 make 命令行变量 `PKG_CONFIG=<abs>` 显式传入**（命令行赋值优先级高于 Makefile 内 `?=`/`=`，不改上游）。
- 适用边界：所有 Makefile 用 `PKG_CONFIG?=$(shell which pkg-config)` 的包。

### 4.3 `fatal error: X11/Xlib.h file not found`

- 根因（两条叠加）：
  1. 上游 Makefile 编译规则 L78 只引用 `$(CFLAGS)`，**全文不引用 `CPPFLAGS`**；
  2. conan `AutotoolsToolchain` 把依赖 include 目录放进 `CPPFLAGS`（而非 CFLAGS），
     且本包未加 `AutotoolsDeps`/`PkgConfigDeps` ⇒ clang 拿不到任何依赖头目录。
  上游 Makefile L58 本应由 pkg-config 补 `-I`，但见 4.4 的 .pc prefix 问题。
- 最终方案：`_dep_flags()` 从 `self.dependencies.host`（含传递可见的 xorgproto/xtrans/libxcb）取
  真实 `package_folder` + `aggregated_components().includedirs` 拼 `-I`，
  用 **shell 变量前缀** `CFLAGS="$CFLAGS <incs>" make ...` 注入。
  ⚠ 不能用 `make CFLAGS=...` 命令行变量：命令行赋值会让 Makefile L31-33/L58 的 `CFLAGS+=` 全部失效
  （丢掉 `-std=c99` 与 `-DVERSION/-DMANPAGE_PATH` 烧录）。
- 命中知识：`knowledge/drafts/DRAFT-E2186-autotools-deps-missing-dep-flags.kv`
  L26 title「Conan autotools 配方只调 AutotoolsToolchain 时依赖的 -I/-L 不注入」——
  与本包 4.3/4.4 两条错误同类；其 rec 是补 `AutotoolsDeps`，本包取 clipnotify/1.0.2 的手工 -I/-L 形态（裸 Makefile 无 configure 可用 helper）。

### 4.4 `ld.lld: error: unable to find library -lX11`

- 根因：`pkg-config --libs` 给出的 `-L` 来自依赖包**自带**的 `<pkg>/lib/pkgconfig/*.pc`，
  其 `prefix=` 是**构建机当时**的 conan 缓存绝对路径（本包的 libx11/libxrandr/libxinerama 是从 ohpcd 拉的
  二进制，路径前缀与本机不同）⇒ `-L` 全部指向不存在目录；而 `AutotoolsToolchain` 又不像 `CMakeDeps`
  那样把依赖 libdir 写进 `LDFLAGS`（Makefile L82 链接行确实用了 `$(LDFLAGS)`，但值是空的）⇒ 无有效 `-L`。
- 已试过的失败方案：只把 PKG_CONFIG_PATH 作用域注入（各依赖 lib/pkgconfig + generators）——
  .pc 找到了但 prefix 仍旧，`-L` 依然无效。
- 最终方案：同一 `_dep_flags()` 生成的 `-L<本机真实 libdir>` 以 `LDFLAGS="$LDFLAGS <libs>"` 前缀注入；
  `-lX11 -lXrandr -lXinerama` 仍由上游 pkg-config 提供（保持上游链接语义）。
- 命中知识：`knowledge/drafts/DRAFT-ccfits-2.7-stale-pc-prefix-regen.kv`
  L26 title「依赖包自带 .pc 的打包时绝对 prefix 在消费端失效：必须用 PkgConfigDeps 重新生成而非沿用，
  PKG_CONFIG_PATH 注入是必要非充分条件」，L37 affected_scope「上游用 pkg-config 探测依赖
  （CMake PKG_CHECK_MODULES、meson …）」——本包是该族的第三种形态（裸 Makefile `$(shell pkg-config)`）；
  正式条目 `knowledge/graph/E355.kv` L38/L39 覆盖 `.pc prefix` 修正族（meson 场景）。

### 4.5 为什么不用 `make install`（package() 显式 copy）

读了 Makefile 全文 115 行：install 目标确实存在（L96），但两条前置在鸿蒙机上都不成立：

- L92-94 manpage 规则依赖 L84-86 的 `md2man-roff $^ > $@`（L86 原文用自动变量 `$^`，不是 `$<`）生成手册页，设备 `command -v md2man-roff` → MISSING；
- L88-90 / L92-94 两条安装命令都用 `install -Dm 755`，设备 `command -v install` → MISSING。

⇒ `package()` 显式 `copy()` 三件：`obj/xininfo → bin/`、`doc/xininfo.1 → share/man/man1/`
（tarball 自带上游已生成的手册页，不需要 md2man）、`LICENSE → licenses/`。
同时 build() 用 `PREFIX=<package_folder>` 编译，使 Makefile L33 烧进二进制的 `MANPAGE_PATH`
（= `$(PREFIX)/share/man/man1/xininfo.1`，L25）指向包内真实安装位置。
实测该路径可用：conan 2.29 在 build 阶段 `self.package_folder` 已解析
（日志 `xininfo make PREFIX (baked MANPAGE_PATH root) = .../p/b/xinine.../p`）。

### 4.6 E077 ELF 自签

产物在 `build()` 内、`copy()` 进包之前完成签名（llvm-objcopy 去旧段 → binary-sign-tool -selfSign 1 → chmod 0775），
`copy()` 不改字节 ⇒ 包内产物与 `.codesign` 同源；A2 断言即在包内产物上验证 `.codesign` 存在。

## 5. 依赖发布态（W0/R35/R36）

| 依赖（`conanfile.py:63-65` 的精确 requires，**无 user/channel**） | 版本 | 随 PR 可解析证据 | 本轮独立只读探针 |
|---|---|---|---|
| libx11 | 6.4.0 | `reports/w3-local-ci.log:32` `[ok] dependency in registry: libx11/6.4.0` | `conan search libx11/6.4.0 -r=ohpcd` → `Found 1 pkg/version recipes matching libx11/6.4.0 in ohpcd` |
| libxrandr | 1.5.5 | `reports/w3-local-ci.log:34` 同形 | `conan search libxrandr/1.5.5 -r=ohpcd` → `Found 1 pkg/version recipes matching libxrandr/1.5.5 in ohpcd` |
| libxinerama | 1.1.6 | `reports/w3-local-ci.log:33` 同形 | `conan search libxinerama/1.1.6 -r=ohpcd` → `Found 1 pkg/version recipes matching libxinerama/1.1.6 in ohpcd` |

证据形态说明（本轮改正，对应一条外部审计意见）：上一版此表写「`conan download <名> -r=ohpcd --only-recipe` → 日志含 `Downloading recipe`」，但**`Downloading recipe` 这串字在本任务任何日志里 0 命中**（只出现在任务私有脚本 `s3.sh:12`/`s4.sh:26` 与台账 `STATE.md:19` 的文字里），随 PR 的件里没有该读数 ⇒ 读者无从复算，该形态已删除。现只给两种可解析形态：**①** 随 PR 的 `reports/w3-local-ci.log:31-34`，即框架 R36 远端闸 `L0i: Checking dependency availability in registry (R36)...` 的原文三行；**②** 本轮另跑的只读探针 `conan search <精确名> -r=ohpcd`（`CONAN_HOME=~/tmp/ch/home-xininfo`，匿名连远端，三枚各 `Found 1 pkg/version recipes`），落盘 `~/tmp/uc2/z44-xininfo/dep-search-r2b.txt:1-9`（任务私有、未随 PR，命令可原样复跑）。⛔ 不用通配 `conan list` 判 binary；`reports/w3-local-ci.log:174-180` 的 `- Cache` 与其后的`Already installed!` 是**本地缓存形态**，按规范属"假成功形态"，**不当发布态证据**。

版本组合取同仓已合并消费者 marco/1.26.2 的同款（其 L107/L111/L115 即这三件）。
`bash ci/scripts/preflight_check.sh xininfo/0.14.11`（配方就位后复跑）的设备控制台读数为 `[OK] 已发布: libx11/6.4.0 / libxinerama/1.1.6 / libxrandr/1.5.5`、`[OK] 版本号未被占用: xininfo/0.14.11`、rc=0。该控制台输出**未随 PR**，其随 PR 的等价机器行是 `reports/w3-local-ci.log` 的 `:31-34`（L0i 依赖在远端 registry）与 `:35-36`（L0j 版本号未被占用：`[ok] version not in registry yet (first publish)`）。

## 6. 已知未决 / 风险

1. `L2_RESULT=skip`（框架预期：CI 裸跑包内 bin 不载 conanrun 环境，libX11.so.6 不在裸 LD_LIBRARY_PATH）——
   不作为可执行证据；真正的可执行证据是 L1 的 A1-A6（test_package 在 conanrun 下执行包内产物）。
2. `finish` 本轮实读（输出件 `~/tmp/uc2/z44-xininfo/finish-r2.log`，任务私有、**未随 PR**，故本条给结论+出处行号，外部读者请按 §2 的随 PR 机器行复算）：`[10/10] submit 就绪预检` 报 **3 项未就绪**（`:106` reports/test-report.md、`:107` packaging/、`:108` `.staging-verified`；`:109` build-closed marker 已 ✅，`:110` "3 项未就绪，submit 前需修复"）；`step8` 为 `:101` `gen_summary 失败: str object has no attribute append`（框架 SUMMARY.md 生成器缺陷）；`step5b` 为 `:95` 知识图谱完整性检查 + `:96-99`（`notes.md: total=0 extracted=0`、`manifest.yaml: knowledge_count=4 unreferenced=4` ⇒ "存在知识遗漏"告警，四条见版本级 manifest `:27-31`）。**失败步骤实读 = step5b, step8（`:112`），其中没有 step2** —— 上一版此处写"step2 同因 close-archive 未落标记"是与 `:112` 不符的错引，已改正（`close-archive` 恰恰已成功，见 `:109` build-closed marker ✅）。两者都不在 W3 判决链上：W3 判决读数是 `:66` `✅ W3 本地 CI 模拟通过` 与 `.ci-result.json` 的`exit_code: 0`（其 `log_sha256` 与当前 `reports/w3-local-ci.log` 的 sha256 逐字相等）。这三类按 SKILL 表格均为"警告/非阻塞"，但 `run`/`submit` 路径可能要处理，且 step5b 要把 notes 改成框架解析器认的条目格式才算清 —— 均交主理裁，本子代理未动框架文件、未动 `knowledge_gained` 清单。
3. 首轮 W3 曾被 `junk_check` 以 **full 模式**（整仓 85512 文件）拦下 2 项**他人包**存量违规：
   `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`
   （JC1/JC5，均为 git 已跟踪文件）。根因是本地无提交时 `git diff origin/main...HEAD` 为空 ⇒ 回退 full 模式；
   把本包 9 个文件提交后即回到 incremental 模式，`JC_RESULT=pass`。
   ⇒ 这 3 个他人包遗留文件仍在 main 上，任何 worktree 在"无提交"状态下跑 W3 都会被它们误拦 → 建议单独治理。
4. `conandata.yml` 在 W3/verify 期间被框架临时注入 ghfast/gh-proxy 镜像（原文读数 `reports/w3-local-ci.log:97` `Mirror fallback: rewriting source URLs in conandata.yml...` 与 `:100 found 5 source URL(s)`，而提交版 `conandata.yml:12` 只有 1 条 url），收口前须从 HEAD 还原为"仅官方直链"版本；本文提交态 `grep -c -i -E "gh-proxy|ghproxy|gitclone|kkgithub" conandata.yml` = 0。`reports/`、`ci-metadata.json` 都在 .gitignore 内 ⇒ 随 PR 的两件判决日志是 `git add -f` 显式带上的（见 §6.6），`ci-metadata.json` 不带。
   **W3 通过态的准确措辞是下面两句并列，缺一不可**：① 通过 W3 的是**框架镜像改写态的 conandata**（构建输入即该改写态，recipe revision 随 URL 形态变）；② 提交版官方直链由**本轮独立复验**担保：`curl -sSL -L` 该链 `http=200`、`size_download=6420`、`sha256 = 53a9fc4df54d36fd2640c7a65f90c345ed7306e24d3a3a27629b12fb858aed5b`，与 `conandata.yml:13` 的 pin 逐字相同；W3 用的又是同一枚已缓存的 6420B tarball，源码字节与 pin 同源，差异只在 URL 形态。⇒ 不写"提交版配方单独通过了 W3"这种不成立的句子。
5. PF8（CLI 包必须有软件级 `commands.json`）与 PF9（archives 变更路径须 ≥5 段，即必须落在 `包/版本/` 下）
   对**新增 CLI 包**互斥：软件级三件套只有 4 段。先例 `archives/v/vamps`（commit `ec60ece1de`，2026-09-21，
   已在 main）在同一 commit 内同时提交软件级 `commands.json`/`manifest.yaml`/`README.md` ⇒ 本包按先例提交。
---
6. **随 PR 的证据件收缩为两件**：`reports/w3-local-ci.log`、`reports/conan-create.log`（都用 `git add -f` 显式带上，因 `reports/` 在 .gitignore 内）。框架生成件 `reports/conan-verify-report.md` 本次整改起**不再随 PR 提交**（用 `git rm --cached` 只去跟踪，盘上件原样保留供复算）。理由：它对同一道门给出两种读数——报告 `:42 ## L2: ✅ PASS` 配正文 `:43 ⏭️ 跳过（无 cache 路径）`，`:45-46`(L4)、`:48-49`(L5) 同形；` :3 **Verdict**: PASS`、`:39 ## G4: ✅ PASS` 配正文 `:40 ⚠️ 无法找到程序包 ID`（G4 无判定对象）。⛔ 不改报告正文（那是改证据）。⇒ 本 PR 对 L 级门的**唯一权威读数**是 `reports/w3-local-ci.log:355-359` 的 `*_RESULT=` 机器行，其中 **L2 只有一种读数 = skip**（`:357 L2_RESULT=skip: xininfo version/help failed`），与本文 §2 代码块、§6.1 一致。原先前文指向该报告的锚已全部重指到 w3 日志的等价机器行（G2 ≡ `:341 [ok] xininfo/0.14.11 — conan create passed`；结构面 ≡ `:31-40` 的 L0i/L0j/L0k/L0m）。G1/G2 之"✅ 图标"本身不再被引用；G3（R26 同名库）与 G4 在随 PR 的件里没有机器读数，故本 PR 不为二者主张任何判决。
7. 同一份报告 `:8-15` 记 `**Knowledge hit**: E490` 与 `📦 构建系统: autotools`，并在 `:15` 预测「⚡ G2 conan create 可能因此失败，建议先修复」。该判定是**框架图谱命中面误判**，与本 PR 两个载体直接冲突：版本级 `manifest.yaml:6` 与软件级 `manifest.yaml:7` 均写 `build_system: makefile`；本文 §4.3/§4.5 记录本包是裸 GNU Makefile、无 configure、未加 `AutotoolsDeps`/`PkgConfigDeps`；E490 的作用对象（`configure`/`config.guess`/`config.sub`/`install-sh`/`missing` 这些 helper 脚本）在官方 tag archive 全树 6 个文件里**一个都不存在**（§1 清点，本轮 `tar xzf` + `find -type f` 复算一致）。报告自己的 `:31-32 ## G2: ✅ PASS / ✅ conan create 成功` 也与它 `:15` 的预测相反。⇒ 不改报告正文，改为**不随 PR 提交**（§6.6），此段仅作差异披露；构建系统口径以两级 manifest 为准。
8. 同一份报告 `:4` 把 Reference 写作 `xininfo/0.14.11@ohpcd/stable`（带 user/channel），而 W3 图与日志（`:326`/`:341` 等）、版本级 `manifest.yaml:5 conan_ref: "xininfo/0.14.11"`、`conanfile.py:63-65` 的三枚 requires 均为**无 user/channel** 形态 ⇒ 属框架报告模板残留，与"版本串不得归一化"无关，⛔ 不改报告正文。附带一条否证性只读探针（避免下一个人再踩）：`conan search libx11/6.4.0@ohpcd/stable -r=ohpcd` 返回 `ERROR: Recipe ... not found`，`libxrandr`/`libxinerama` 同 ⇒ **带 @ohpcd/stable 的引用形在本仓是错的**，发布态的正确探针见 §5（不带 user/channel）。

**编译结束**: 2026-09-25 19:26
**最终状态**: built
