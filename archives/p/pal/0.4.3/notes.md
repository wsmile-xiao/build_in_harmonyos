# pal 0.4.3 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile 三层：顶层 `Makefile` 用通配 `%:` 转发到 `src`；`src/Makefile` + `src/Makefile.defs`；`src/convert/Makefile`。无 configure / CMake / meson）
- 编译日期: 2026-09-26
- 编译器: clang（`/data/service/hnp/bin/clang`，取自 `tools.build:compiler_executables` 的 dict 值）
- 构建主机: B 机（HarmonyOS aarch64，profile `ci/conan/profiles/ohos-aarch64`，os.version=6.0）
- CONAN_HOME: `~/tmp/ch/home-pal`（含 `ohpcd` remote）
- 状态: built（由 `ohc-run.py finish pal 0.4.3` 落值，非手工预标；W3 判决见「验证结果」）

> **⚠ 本包 `reports/` 下全部文件不随 PR（`review-memory §19` 的 `*.log` 禁入 + 生成物不入库，2026-09-29 按审查意见删除）**：
> `build-iterations.md` / `conan-create.log` / `conan-verify-report.md` / `test-report.md` / `w3-local-ci.log` **5 件已 `git rm --cached`、磁盘原件保留**（`<worktree>/archives/p/pal/0.4.3/reports/`）；**随 PR 的 `reports/` 件 = 0**。
> ⇒ 下文所有 `reports/...` 坐标（`Using CFLAGS:/CPPFLAGS:/LDFLAGS:` 三行、`make` 旗标 137-139 行、消费者断言、第 5 轮 `rod2-verify5.log` 等）**按本机现件核**、关键读数已内嵌本节，读者不依赖这些文件在库。

## 编译步骤

货源是 upstream canonical 发布位，sha256 一手实测 `ce470cb7be76522ff58cd0325ad7817b6cc2132a5e0cea55de8c9eb63b54551c`
（130865 B，与 Debian 池记录的 upstream 值逐字相等）。

```bash
# 1) 取源码（conan 的 source() 从 conandata.yml 的 url+sha256 下载并 strip_root）
# 2) 打两份补丁（apply_conandata_patches）
# 3) 生成 pkg-config 面：VirtualBuildEnv + PkgConfigDeps + 显式 PKG_CONFIG_PATH
#    （PkgConfigDeps 会产出 glib-2.0.pc / readline.pc / ncursesw.pc，
#     但不会替裸 make 把生成目录放进 PKG_CONFIG_PATH，故另写一个 buildenv 脚本）
# 4) 编译（唯一的 make 调用）
make -C src -j1 \
     CC=/data/service/hnp/bin/clang \
     STRIP=true \
     OPT="-O2 -Wall" \
     prefix="<package_folder>"
```

上游 `info:` 目标会在编译前把解析结果打回日志，是旗标注入是否真的生效的机器证据
（`reports/conan-create.log` 里 `Using CFLAGS:` / `Using CPPFLAGS:` / `Using LDFLAGS:` 三行；
为保证该回显确实落在证据文件里，最后一轮先 `conan remove "pal/0.4.3@ohpcd/stable" -c`
把本地缓存清掉再跑 verify，逼出真实重建——注意引用必须带 `@ohpcd/stable`，
不带 user/channel 的 `conan remove "pal/0.4.3"` 删的是另一个引用、缓存仍在，G2 会走缓存复用）：

```
Using CFLAGS: -O2 -Wall
Using CPPFLAGS: -I<glib>/include -I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include \
                -I<readline>/include -I<ncursesw>/include \
                -DPAL_VERSION="0.4.3" -DPREFIX="<package_folder>"
Using LDFLAGS:  -L<glib>/lib -L<readline>/lib -L<ncursesw>/lib \
                -lglib-2.0 -lm -lpthread -ldl \
                -lreadline -lhistory -lformw -lmenuw -lpanelw -lncursesw -lintl
```

> ⚠ 读日志时别被误导：补丁 0001 只把 strip 的**命令**换成了可覆盖的 `$(STRIP)`，
> 而 `echo " [strip] $(NAME)"` 这行标签是无条件打的 ⇒ 日志里仍会出现 `[strip] pal`，
> 但实际执行的是 `true`。"有没有真被 strip"的机器证据是符号表：
> `size 801216 | has .symtab: True | has .shstrtab: True`（见「验证结果」末段）。

## 路径 B 声明（3+2）

- **适配路径**：路径 B（配方适配 + 知识库扩展；本文件与知识草稿、Issue 互链）
- **使用知识库**：`knowledge/graph/E098.kv:11,25-29`（设备无 `install` 命令 ⇒ `cp`+`chmod` 手工安装）；`knowledge/graph/E077.kv:3-5` 加 `knowledge/drafts/DRAFT-yices-2.7.0-llvm-strip-exec-denied.kv:27`、`knowledge/drafts/DRAFT-ohos-elf-skip-strip-codesign.kv:43-44`（strip 使 OHOS ELF 不可执行 ⇒ 优先让上游别 strip；同症状已合入先例 `archives/a/abduco/0.6/conanfile.py:46,53,57`）；`knowledge/drafts/DRAFT-hoedown-3.0.7-makefile-cflags-override.kv:26-31,38-39` 与 `knowledge/drafts/DRAFT-smemstat-0.02.13-make-cli-cflags-override.kv:9-12`（裸 Makefile 用普通 `=` ⇒ make 忽略环境变量、命令行赋值整体覆盖，须重供完整 flag 集）；`knowledge/drafts/E583-draft-AB57.kv:15,22-23`（ncurses 制品只发布宽字符库——层次差：该条讲 autotools 探测期，本包是裸 Makefile 链接期，故只作机制引用）；`knowledge/graph/E123.kv:7,38,94`、`E107.kv:7`、`E508.kv:9,14`、`E015.kv:10,27-29`（`g_libintl_*` 运行期符号族与 `-lintl` 处方）
- **知识库扩展**：`knowledge/drafts/DRAFT-pal-0.4.3-readline-private-function-typedef-not-exported.kv` 与同 stem `.md`（成对随本 PR 提交；本包一手撞到的新机制）
- **关联 Issue**：#3469（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3469）
- **分支/提交**：`feat/pal-0.4.3`，逐轮 sha 与署名分布见 PR 正文「分支/提交」行（该行的提交数与 sha 每轮整改后重取，不以本文件为准）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 环境变量里设了 CFLAGS/LDFLAGS，编出来的二进制却没带 conan 的 include/lib 路径（看着绿、实际没注入） | `src/Makefile.defs` 全部用普通 `=` 赋值（不是 `?=`）⇒ make **忽略环境变量 CFLAGS/LDFLAGS**，而命令行赋值会整体替换表达式；`CFLAGS = ${OPT}` | 走命令行整体注入，且注入点选 `OPT`（`CFLAGS` 的唯一来源），不碰 `CPPFLAGS/LDFLAGS` 好让补丁的 pkg-config 行继续算依赖旗标 |
| 2 | 上游写死的 `-lncurses` 在本仓依赖树下不可用；intl 侧的一手观察发生在**运行期**：`Error relocating ... g_libintl_gettext: symbol not found`（`~/tmp/uc2/z71-pal/explore/help.txt:1-12`，同批还有 `g_ascii_strdown`、`g_date_new` 等 10 个以上符号一起报，属不带 runenv 裸 exec 的加载失败） | conan 的 ncurses 制品**只提供宽字符库**——在 conan 依赖树内 `find $CONAN_HOME -name libncurses.a` 命中 0、该 ncurses 包的 lib 目录里只有 `libncursesw.a` 与 `libncurses++w.a`（⚠ 量词只覆盖本仓依赖树：设备 `~/.harmonybrew/lib/libncurses.a` 是另一套 ncurses 6.6 的软链，与本配方链接的依赖树无关，W4 第二轮实测） ⇒ 不改必链不上（⚠ 这一句是**结构性推断，不是本轮观察**：本包所有构建轮都跑在已打补丁的 Makefile 上，日志里 `cannot find -l`、`unable to find library`、`undefined reference`、`collect2` 命中数均为 0，从未产生过未修复的链接现场）。intl 侧：`libintl.h` 与 `libintl.so` 在 glib 制品内，而 conan 生成的 `glib-2.0.pc` 只展开出 `-lglib-2.0 -lm -lpthread -ldl`、不含 `-lintl`，与 `conan-create.log:139` 的 LDFLAGS 尾部唯一那枚 `-lintl` 对得上 ⇒ 该旗标要显式补 | 补丁 0001 把 `INCLDIR`/`LIBS` 改成反引号跑 `pkg-config --cflags/--libs glib-2.0 readline`（readline.pc 的 `Requires: ncursesw` 自然带出 `-lncursesw`）并补 `-lintl`；配方 `tool_requires("pkgconf/3.0.5")` 保证 pkg-config 在 PATH 上 |
| 3 | `manage.c:406` clang 报 `expected expression` / `use of undeclared identifier` | 上游用了 readline 的**私有宏** `Function` | 补丁 0002 换成公开类型 `rl_hook_func_t *`，`MAKE_RC=0` |
| 4 | ★ 链出来的 `src/pal` 一执行就 `Operation not permitted`（rc 126） | **OHOS 上被 strip 过的 ELF 不可执行**；上游链完无条件 `strip $(NAME)` | 补丁 0001 把 strip 变成可覆盖变量 `$(STRIP)`，配方传 `STRIP=true` ⇒ 同一枚二进制立刻可加载。先例 `abduco/0.6` 同症状同处方。⛔ 不走 E077 四步重签、⛔ 不把消费者断言降级成"只查存在不执行" |
| 5 | 打包阶段 `TypeError: rename() missing 1 required positional argument: 'dst'` | `conan.tools.files.rename` 的签名是 `(conanfile, src, dst)`，不是 `os.rename` | 改用 `os.rename`（并去掉多余导入） |
| 6 | `ERROR: Can't open file: /etc/pal.conf` + `ERROR: Can't open file: <PREFIX>/share/pal/pal.conf` + `ERROR: This indicates an improper installation.`，日历能画但一条事件都不读 | `src/input.c:570-582` 引导 `~/.pal/pal.conf` 的回落顺序是 `/etc/pal.conf` ⇒ `PREFIX/share/pal/pal.conf`；而上游 `install-share` 把模板装到 `${DESTDIR}/etc`——**与 `$(prefix)` 无关**，在 conan 包/非 root 场景里那个位置根本不可达 | `package()` 把 `pal.conf` **同时**放进 `share/pal/pal.conf`（运行期真正回落的那份）与 `etc/pal.conf`（upstream 原语义位置）。修完第 5 条消费者断言从 FAIL 转 `[ok]` |
| 7 | `ERROR: ... Error in build() method, line 102 → ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list` | Conan 2.29 不支持该 conf 的 `:c` 子键取法；**仓内 `templates/conanfile-makefile.py.tmpl` 用的正是这个坏形式** | 按 `abduco/0.6` 先例取 dict 再索引：`self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` → `.get("c", "clang")` |
| 8 | `make install` 走不通 | 设备**没有 `install` 命令**且非 root（上游用 `install -m 0755 -o root`），install 目标里还有交互式 `rm -ri` 与 `msgfmt`（po）/`gzip`（man）依赖 | `package()` 自己拷交付物，完全不碰 `make install` |

## 源码修改

两份补丁，与 `patches/` 目录成对：

- `patches/0001-Makefile-pkg-config-deps-and-strip-override.patch`
  `src/Makefile`：`INCLDIR`/`LIBS` 改由 pkg-config 解析并补 `-lintl`；无条件 `strip $(NAME)` 改为 `$(STRIP) $(NAME)`。
  `src/Makefile.defs`：新增 `STRIP = strip` 默认值（保持非 OHOS 平台行为不变）。
- `patches/0002-manage.c-readline-public-hook-type.patch`
  `src/manage.c`：`rl_pre_input_hook = (Function*)` → `(rl_hook_func_t *)`。

## 依赖版本

编译期精确钉（`preflight_check.sh pal/0.4.3` 四个全 `[OK] 已发布`，`conan install --build=never` 三依赖全 `Already installed`）：

- `glib/2.84.0.1`（glib/gobject/gio + `libintl`）
- `readline/8.3`
- `ncurses/6.6`（只有宽字符库）
- `pkgconf/3.0.5`（tool_requires）
- 传递：`libffi/3.4.4`、`pcre2/10.45`、`zlib/1.3.1.1`

## 验证结果

```bash
# ── W0 货源与依赖 ──────────────────────────────────────────
$ preflight_check.sh pal/0.4.3                    # 见 ~/tmp/uc2/z71-pal/preflight-recipecp.log
[OK] 已发布: glib/2.84.0.1
[OK] 已发布: ncurses/6.6
[OK] 已发布: pkgconf/3.0.5
[OK] 已发布: readline/8.3
[OK] 版本号未被占用: pal/0.4.3
[OK] 所有依赖均已发布到制品仓，可以安全开始适配 pal/0.4.3      PREFLIGHT_RC=0

# ── W2/R36/W3 一键验证 ─────────────────────────────────────
$ ohc-run.py conan-verify pal 0.4.3               # VERIFY_RC=0
  ✅   G1: PASS
  ✅   G0: PASS
  ✅   G2: PASS
  ✅   G3: PASS
  ✅   G4: PASS
✅ 配方验证通过: pal 0.4.3

# 本地 CI 仿真（reports/w3-local-ci.log）
G0_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: pal version/help failed          # 见「注意事项」第 1 条
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
KC_RESULT=pass
JC_RESULT=pass

# ── 消费者断言（真跑，逐条执行交付的 ELF）───────────────────
$ bash test.sh <tmpdir>                           # conanrun 环境内
[ok]   --version reports the packaged release
[ok]   --help prints the option block
[ok]   -h prints the copyright banner
[ok]   renders a month grid for -d 09/2026
[ok]   empty-HOME fallback reads the packaged share/pal data
Reading: <pkg>/share/pal/us.pal
Reading: <pkg>/share/pal/christian.pal
Reading: <pkg>/share/pal/history.pal
Reading: <pkg>/share/pal/world.pal
Done reading data (1043 events, 4 files).
consumer assertions: 5/5 passed
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":5,"passedCount":5}

# ── 未被 strip 的直接证据 ──────────────────────────────────
size 801216 | has .symtab: True | has .shstrtab: True

# ── 收尾 ──────────────────────────────────────────────────
$ ohc-run.py finish pal 0.4.3                     # FINISH_RC=2（见下），收尾落值
EXIT_REASON: finish_success
     状态:     built
     补丁:     2 个
  ✅   ✅ 仅含配方变更 (12 文件)，无框架文件      # W2 原子性
```

### 五维账本

| 维度 | 数量 | 依据 |
|------|------|------|
| 静态总数（上游声明的用例数） | **0** | `src/Makefile` 目标只有 info/debug/install*/uninstall*/pot/clean*/dist/srpm/splint/libpal.a；无 `TESTS`/`add_test`/ctest。`grep -c` 逐文件计数：14 个 `src/*.c` 全 0，`src/convert/ical2pal.c` 1（是 `-lical` 链接行的误命中，非用例） |
| 可执行数 | **0** | `make -C src check` → `make: *** No rule to make target 'check'.  Stop.`（一手日志 `~/tmp/uc2/z71-pal/smoke5.log` 末段） |
| 实测通过数 | **0** | 同上，无上游用例可跑 |
| 跳过数 | **0** | 没有"存在但因平台原因跳过"的上游用例 |
| 失败数 | **0** | 同上 |

> 上游分母为 0 是**实测结论**，不缩分母也不造分母。rule12 要求的"≥1 条真实执行"由
> **消费者用例**满足：`test_package/test.sh` 5 条，全部真跑，`passedCount=5`（见上 HMBS 标记行）。

### 证据与日志路径

仓内（随 PR）：
- `archives/p/pal/0.4.3/reports/conan-verify-report.md`
- `archives/p/pal/0.4.3/reports/conan-create.log`（make 旗标回显在 137-139 行，消费者断言在尾部）
- `archives/p/pal/0.4.3/reports/w3-local-ci.log`
- `archives/p/pal/0.4.3/reports/test-report.md`

设备侧（本机断点目录 `~/tmp/uc2/z71-pal/`，第一棒 + 本棒）：
- 第一棒：`preflight-deps.log`、`conanhome-init.log`、`dep-flags.log`、`explore-smoke.log`、
  `explore/build2.log`、`strip-probe.log`、`smoke4.log`、`smoke5.log`、`genpatch.log`、
  `genpatch2.log`、`commit1.log`、`ref-abduco.log`、`ref-2048.log`、`facts*.log`
- 本棒：`rod2-build.log`、`rod2-initbuild.log`、`rod2-initbuild2.log`、`rod2-verify1..5.log`、
  `rod2-finish1.log`、`preflight-recipecp.log`、`recipe-backup-164046/`

## 交付物

`bin/` 集合差已核对：**只声明 `pal`，包内 `bin/` 也只有 `pal`**，不多不少（`commands.json` 为软件级）。

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/pal` | 801216 B | 主程序，**未 strip**（含 `.symtab`），动态链接 glib/readline/ncursesw/intl |
| `etc/pal.conf` | 4210 B | upstream 原语义位置（`install-share` 装到 `${DESTDIR}/etc`） |
| `share/pal/pal.conf` | 4210 B | ★ 运行期真正回落的那份（缺它即报 improper installation） |
| `share/pal/*.pal` | 11 个 | australia/austria/birth-death/christian/computer/history/lotr/music/pagan/us/world |
| `share/man/man1/pal.1` | — | 由 `pal.1.template` 直接取用（实测模板里 `PAL_VERSION` 占位出现次数为 0，且设备无 gzip ⇒ 不生成 `.gz`） |
| `licenses/LICENSE` | — | 上游 `COPYING`（GPL-2 正文；源码头注明 "any later version" ⇒ GPL-2.0-or-later） |

**范围决策（不是失败）**：`src/convert/` 的 `ical2pal`/`pal2ical` 需要 **libical**（`-lical -lpthread`），
`vcard2pal` 经一手实测是 **awk 脚本**（2024 B，`#!/usr/bin/awk -`，不是 ELF，且 `src/convert/` 全成员 mode 644 无执行位）。
本轮 convert 工具**不进交付面**：为一个附带工具去引 libical 或 vendor 源码不划算，且它不影响 `pal` 主功能。
因此 `commands.json` 只声明 `pal` 一条命令。

## 注意事项

1. **本包是动态链接的，运行依赖 conan runenv。** 按绝对路径裸跑交付的 ELF 会：
   ```
   Error loading shared library libglib-2.0.so.0: (needed by .../bin/pal)
   Error loading shared library libintl.so.8: (needed by .../bin/pal)
   Error relocating .../bin/pal: g_ascii_strdown: symbol not found
   ```
   ⇒ 这正是本地 CI 里 `L2_RESULT=skip: pal version/help failed` 的**唯一原因**（不是旗标不支持：
   `main.c:422/569` 明确实现 `--help`/`--version`，conanrun 环境内两条断言都 `[ok]`）。
   在 conanrun 里（`test_package` 走的就是这个环境）执行完全正常，5/5 通过。
   静态链接可以消掉这个 skip，但本轮没有采用：一是 `abduco`/本包先例的处方都是"修运行环境"，
   二是改静态链需要 glib+pcre2+libffi+zlib 一并静态并披露，属于范围变更，留给主窗定夺。
2. **prefix 被编进二进制 ⇒ 包不可跨机重定位。** `-DPREFIX="$(prefix)"` 指向 conan 包目录
   （`~/tmp/ch/home-pal/p/b/<hash>/p`）；换机器/换 CONAN_HOME 后 `share/pal/*.pal` 与
   `share/pal/pal.conf` 会找不到（程序仍可执行、`--version`/`--help` 仍正常，只是读不到自带日历数据）。
   最终交付（cmd-pkgs）若安装到固定前缀，需要按那个安装路径重新编译或以 `/usr` 为 prefix 重建。
3. `head -30` 一类的旧日志 grep 会串台：`rod2-verify1/2` 是修 `pal.conf` 之前的失败记录，
   权威判决以第 5 轮 `rod2-verify5.log`（磁盘留档）与 `reports/conan-verify-report.md`（**该件按 §19/生成物不随 PR、磁盘留档**）为准。
4. 门禁的软跳过项（不阻塞，但别当"真跑过"报）：verify 报告里 `G4: ⚠️ 无法找到程序包 ID`、
   `L2/L4/L5: ✅ PASS` 配 `⏭️ 跳过（无 cache 路径）`——权威的 L2 结论取 `w3-local-ci.log` 的 `L2_RESULT=skip`。
5. `finish` 的 `FINISH_RC=2` 是收尾清单未全齐（`reports/test-report.md` 当时缺、`packaging/` 与
   `.staging-verified` 属 submit 前项、`gen_summary` 抛 `'str' object has no attribute 'append'`），
   不是编译失败——它自己的判决行是 `EXIT_REASON: finish_success` 并落了 built。

### 设备/框架侧发现（未自行动手，交主窗定夺）

1. `scripts/ohc/check_env.py:33` 是 `except Exception:` 却引用 `str(e)` ⇒ `NameError: name 'e' is not defined`。
   触发条件：设备上 `~/usr/local/bin/automake` 是**悬空 symlink**（`shutil.which` 能找到、exec 抛 ENOENT）。
   后果：`init-build` 的 Step1 必炸 ⇒ `ohc-run.py build` 走不通（本棒改走 `conan-verify`，其不依赖 build context）。
   `check_env()` 的返回值在 `init_build.py:543` 并未被使用，纯信息输出，属 nuisance crash。
2. `templates/conanfile-makefile.py.tmpl` 里 `self.conf.get("tools.build:compiler_executables:c", ...)`
   在 Conan 2.29 上是坏形式（见问题表第 7 条），照抄模板的配方会在 build() 第一行炸。
3. 以上两条都属框架件，按纪律本棒未改（框架改动须单独 PR）。

### 对话 #1（本棒：配方收口）

问：第一棒的结论能直接用吗？
答：能。侦察与探索编译都有一手日志（`~/tmp/uc2/z71-pal/`），本棒只做收口，未重做侦察。

问：五把适配点在 conan 里怎么接？
答：①旗标走命令行 `OPT=`（因为 `Makefile.defs` 全用普通 `=`，env CFLAGS 无效）；
②依赖旗标交给补丁 0001 的 pkg-config 行 + 配方 `PkgConfigDeps` + 显式 `PKG_CONFIG_PATH` + `tool_requires(pkgconf)`；
③readline 私有宏由补丁 0002；④strip 由补丁 0001 变成 `$(STRIP)`，配方传 `STRIP=true`；
⑤`make install` 完全不用，`package()` 自己拷。

问：消费者测试只查存在性行不行？
答：不行（门禁纪律也不许）。5 条断言全部真执行 ELF，其中"空 HOME 回落读 `PREFIX/share/pal/*.pal`"
一条恰好抓出了真实缺陷（pal.conf 位置），见问题表第 6 条。

状态：built（`ohc-run.py finish pal 0.4.3` 落值，与 `manifest.yaml` 的 `status` 逐字相同）

---

**编译结束**: 2026-09-26 16:54
**最终状态**: built
