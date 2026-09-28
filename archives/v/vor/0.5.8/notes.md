# Variations on Rockdodger (vor) 0.5.8 — 适配记录

> 窗口：主理-75 子代理 · 构建机 = B 机（HarmonyOS PC aarch64）· 2026-09-27
> worktree `~/qzy/主理-75-vor-0.5.8` 分支 `feat/vor-0.5.8` 基线 `48d9cee684`
> 任务号 11745（主窗持有；本子代理不碰平台、不碰登记表、不建 PR）

**最终状态**: built（本地 `conan-verify` 判决 PASS：G0/G1/G2/G3 实检，**G4 是空判**——正文只有
"⚠️ 无法找到程序包 ID" ⇒ conan-verify 的实际覆盖为 G0-G3（逐字见 `reports/conan-verify-report.md:39-40`）；L2/L4/L5 判决 PASS 但实为"⏭️ 跳过（无 cache 路径）"，等价证据由本窗手工补齐，见「运行期能力实测」）。
未 upload、未合入，故不标 `published`（R29/R37 口径：published 需 CI upload 成功）。

---

## 1. 软件与构建系统

| 项 | 值 |
|---|---|
| 软件 | Variations on Rockdodger（VoR），太空躲陨石街机游戏 |
| 版本 | 0.5.8（上游版本号，未加适配后缀 ⇒ 无 `.1`，与 `vor-0.5.8/` 目录、分支、任务版本完全一致） |
| 许可 | GPL-2.0-or-later（`Makefile.in`/`main.c` 头 + `README.md`「released under the GNU GPL」；音频 public domain） |
| 主页 | https://sametwice.com/vor （README.md 原文） |
| 语言 | 12 枚 `.c` + 14 枚 `.h`（与任务声明 c/cpp 一致 ⇒ 无语言不匹配红线，不触发 env_unsupported） |
| 构建系统 | autotools（tar 内自带 **预生成** `configure`(166325B, GNU Autoconf 2.69) + `Makefile.in` + `aclocal.m4` + `autom4te.cache` + `install-sh`） |
| 产物 | `bin/vor` 单可执行（424384 B, ELF64 / AArch64 / PIE）+ `share/vor/` 61 枚数据文件 + `licenses/COPYING` |
| 包类型 | `package_type = "application"`（无库、无头文件 ⇒ commands.json 必须有，R38/L0k/PF8） |

**不 autoreconf 自举**：上游 `INSTALL:13-16` 原文（**跨行连读的节选**：13-14 两行 + 空行 + 16 行，16 行行首
是制表符、词间多个空格，本处归一为单空格）是 "If you are building from git, (or editing the graphics)
you will also need: autoconf version 2.63 or greater" ⇒ 需要 autoconf ≥ 2.63 的是**从 git 构建**与
**改动图形资产**这两条路径（此前写作「只在从 git 构建时需要」把括号那一支截掉了）；本包两条都不走，
且仓库**没有 `Makefile.am`**
（`Makefile.in` 是手写的，只有 `AC_CONFIG_FILES([Makefile])`）⇒ 自举会直接失败。上游另有
`Makefile.win` / `Makefile.win_cross`（Windows 专用，本包不使用）。

## 2. 取源（R39 判断依据，本窗实测）

采用 **Debian 官方主仓 `.orig`**：
`https://deb.debian.org/debian/pool/main/v/vor/vor_0.5.8.orig.tar.gz`
sha256 `9003089708327e1a3169b412e16725ccb669dd21465d49abec5aa4e6e4cce09a`（361789 B，实测 GET 200 + 设备侧实物哈希一致，解包目录名 `vor-0.5.8`）。

- **没有可用的官方发布物**：上游站 `sametwice.com/vor` 的候选下载路径实测全是同一张 wiki「创建页面」
  catch-all 页（`vor-0.5.8.tar.gz` = **1535 字节**；模板会回显请求路径 ⇒ 同族页 1502–1550 字节，逐条路径与机理见 §13 与 `reports/pf7-source-equivalence-evidence.md:179-236`）；真主页 8591 字节，其上唯一下载链指向 jasonwoof.com 的 `vor-win-0.5.4-rc1.zip`（版本、平台都不对）。
- Debian `.orig` 是**上游原样发布物**（非 Debian 重打包内容，不含 `debian/` 子树），版本号与上游一致 ⇒
  不引入 Debian 修订后缀（R37）。**为什么不能改用上游 GitHub 的 tag 件**（PF7 例外链的后半段）＝现取取证已落成随 PR 的一件：`reports/pf7-source-equivalence-evidence.md`（§0 读数一览 :22-38、两枚 URL 实测 :39-67、两树逐字节对账 :68-105、tag 件缺件 :106-135、`Makefile.am` 计数 :136-146、缺 54 枚 PNG 与再生工具链 :147-178、作者站与 releases API :179-236、后果链 :237-277），摘要与本节口径同步见 §13。
- ⚠ 本窗**未换源、未加任何镜像前缀**：框架的 `get_mirrors()` + trap 会回写 `conandata.yml`，
  提交前已逐文件 `git diff` 核对并还原为官方 URL 标量形态（见 §9 交付核对）。
- 已知风险留报：分类器可能把 pool 址判为「Debian 下游重打包源」。仓内 `origin/main` 已有 304 份
  `conandata.yml` 使用 `deb.debian.org/pool` 址（复算：`git grep -l 'deb.debian.org/debian/pool' origin/main -- 'archives/*/*/conandata.yml' | wc -l` = **304**，本窗 z75z 现取；旧句此处引「metar 以 pool 址成功建 PR」——本仓 `git ls-files | grep -ic metar` = **0**，查无此包归档 ⇒ 该指称已删，「pool 址不阻断」改以可复算的 304 份为据）⇒ 该 finding 不阻断建 PR，
  但 PR 正文需要写明上述判断链（**主窗职责**）。

## 3. 依赖接入（W0/R35/R36）

| 依赖 | 版本 | 取值依据 |
|---|---|---|
| `sdl12-compat` | 1.2.68 | 本仓 SDL 1.2 API 的**唯一提供方**；先例 `archives/s/sdl_image/1.2.12/conanfile.py:37` 与 `archives/s/sdl_mixer/1.2.12/conanfile.py:37` 都写 `requires("sdl12-compat/1.2.68")` |
| `sdl_image` | 1.2.12 | 上游 `#include <SDL_image.h>`、`IMG_Load*` |
| `sdl_mixer` | 1.2.12 | 上游 `#include <SDL_mixer.h>`、`Mix_*` |

- ⛔ **不得使用 `sdl/1.2.x`**：实测 `sdl/1.2.15`、`sdl/1.2.68`、`sdl12-compat/1.2.15` 在 ohpcd 均为「配方不存在」。
- **W0 复核（写 requires 之后再跑一次 preflight）**：
  `bash ci/scripts/preflight_check.sh vor/0.5.8` → 三个依赖全部已发布，`[OK] 预检通过`
  （日志在设备侧 `~/tmp/uc2/z75v-vor/gate1b-dep-recipes.log`，750 B，绝对路径见 §11；**不在本 PR 内**）。
- **R35 正解**：判定用 `conan download <ref> -r=ohpcd --only-recipe` +
  `conan install --requires=... --build=never`（**逐包 `Package installed`**：sdl12-compat `92219b91…`、
  sdl_image `a5f541c2…`、sdl_mixer `9daaf35d…`，传递层 libpng/libjpeg-turbo/libtiff/libwebp/zlib/zstd 全部命中二进制），
  **不用**通配 `conan list` 判断 binary。
- 依赖能力缺口（不是本包缺陷，如实披露）：`archives/s/sdl_mixer/1.2.12/conanfile.py:51-57` 关闭了
  `--disable-music-mod / modplug / midi / ogg / flac / mp3` ⇒ 上游 `sound.c` 要加载的 `mph.xm`（tracker 音乐）
  在该 mixer 下无法解码；`configure` 的 `AC_CHECK_LIB([SDL_mixer],[Mix_InitOgg])` 实测为 `no`
  （无 action-if-not-found，非致命；且 `config.h.in` 的 `HAVE_LIBSDL_IMAGE/HAVE_LIBSDL_MIXER` **源码零引用**
  ——`grep -rn HAVE_LIB *.c *.h` 无命中 ⇒ 这两个检查结果不改变产物）。

## 4. 症状 → 根因 → 最终方案（按发生顺序）

### 4.1 pkg-config 模块名对不上（configure 阶段）
- **症状**：`configure.ac` 用 `PKG_CHECK_MODULES([SDL],[sdl >= 1.2])`（**无 else 兜底**）、
  `SDL_image >= 1.2`、`SDL_mixer >= 1.2`；而 Conan `PkgConfigDeps` 产出的是
  `sdl12-compat.pc / sdl_image.pc / sdl_mixer.pc`。pkg-config **按文件名匹配且大小写敏感** ⇒ 三个都对不上。
- **最小复现**：`PKG_CONFIG_PATH=<generators> pkg-config --exists sdl` → 失败（原始态）。
- **最终方案**：`generate()` 在 `generators_folder` 里以**原文件内容副本**的形式补发上游拼写
  （`Libs`/`Requires`/`Version` 原样保留，仅改写 `Name`/`Description` 并追加 include 拼写的 `-I`）。
  `AutotoolsToolchain` 已把该目录前置进 `PKG_CONFIG_PATH`（conan 源码
  `tools/gnu/autotoolstoolchain.py:311`），无需手工 env，也**不打补丁、不重跑 autotools**。

### 4.2 ★ HMDFS 大小写不敏感把"别名 .pc"变成自引用（链接阶段，本轮最贵的坑）
- **症状**：编译全过、最终链接报 `ld.lld: error: undefined symbol: IMG_Load / Mix_OpenAudio /
  Mix_LoadMUS / Mix_LoadWAV_RW / Mix_PlayChannelTimed …`
  ⚠ **这句链接器原文从未落盘**：本窗对 `reports/` 四件与两个设备侧证据目录全量
  `grep -cE "undefined symbol"` 依次得 conan-create.log=0、conan-verify-report.md=0、
  test-report.md=0、w3-local-ci.log=0、`~/tmp/uc2/z75v-vor/` 全件=0，唯一的 `IMG_Load` 命中是
  configure 的检查回显（`reports/w3-local-ci.log:243`）。⇒ 这一句只是当时现场的**一次性转述**，
  不是随 PR 可核的读数；逐条复算与披露写在 `reports/failure-state-evidence.md` §8（该件 `:221-234`）。
- **第一条真实错误（读数一律以随 PR 的 `reports/failure-state-evidence.md` 为准）**：
  ① `config.log` 里 `pkg_cv_SDL_IMAGE_CFLAGS=''`、`pkg_cv_SDL_IMAGE_LIBS=''`、
  `pkg_cv_SDL_MIXER_CFLAGS=''`、`pkg_cv_SDL_MIXER_LIBS=''` 四格为空，而
  `pkg_cv_SDL_CFLAGS`/`pkg_cv_SDL_LIBS` 有值 —— 逐字摘录在该件 **`:86-91`**。
  ② 同一轮里三格 `PKG_CHECK_MODULES` 的 `--exists` 全 `$? = 0`、configure 结果全 `yes`
  （该件 **`:31-49`**）⇒ "checking 报 yes" 正是假绿。
  ③ 上游 `Makefile.in:44` 把三格 libs 汇进 `SDL_LIBS`、`:46` 的 `ldflags := $(SDL_LIBS) $(LDFLAGS) -lm`、
  `:114` 的链接命令 `$(CC) $^ $(ldflags) -o $@` **只吃 `$(ldflags)`**（模板原文见该件 **`:127-132`**
  与 **`:136-137`**）⇒ 那一轮生成的 `Makefile` 里 `SDL_LIBS` 只剩 `-lSDL-1.2`（该件 **`:115`**）、
  `LDFLAGS` 只剩九枚 `-L` 且**一枚 `-l` 都没有**（该件 **`:101-118`**，其中 LDFLAGS 落在 `:104`），
  `-lSDL_image`/`-lSDL_mixer` 确实进不了链接行。修复态对照见同件 **`:149-154`** 与 **`:158-159`**。
  ⚠ **归属更正**：以上三条原先被挂在 `reports/conan-create.log` 名下，那是**错的**——该件是**成功轮**
  日志，`undefined symbol` 与 `pkg_cv` 在其中 0 命中。故障态现场现已逐字搬进随 PR 的
  `reports/failure-state-evidence.md`（来源件绝对路径 + 摘录当时实算的 sha256 见同件 §0，`:10-26`）。
  ⚠ 另须分清：同件 §2（`:57-67`）里那条 `ld.lld: error: undefined symbol: Mix_InitOgg` 确实落了盘，
  但它出自 `AC_CHECK_LIB([SDL_mixer],[Mix_InitOgg])` 的 conftest 链接、属 §3 末尾的**依赖能力缺口**
  （该 mixer 关掉了 ogg/mod 解码），**不是**本机制的证据。
- **根因（`pkg-config --debug` 实拍；随 PR 可核的那份 = `reports/failure-state-evidence.md:168-192`）**：
  第一版别名写成"只 `Requires:` 前转"的桩
  （`SDL_image.pc` → `Requires: sdl_image`）。**HMDFS 大小写不敏感** ⇒
  `SDL_image.pc` 与 conan 的 `sdl_image.pc` 是**同一个物理文件**，桩把真身覆盖了，于是
  `sdl_image.pc` 自引用；pkg-config 的调试输出：
  `Searching for 'sdl_image' requirement 'sdl_image'` → `Package sdl_image already in requires chain, skipping`
  → `--cflags/--libs` 返回**空**（且 `--exists` 仍返回 0，所以 configure 打印 "checking for SDL_IMAGE... yes" 骗过了所有人）。
  `sdl`/`sdl12-compat` 两个拼写不同名 ⇒ 幸存，这就是"只有 image/mixer 缺符号"的原因。
- **最终方案**：别名一律**读回原 `.pc` 内容后改写**（不再 `Requires` 前转）⇒ 大小写敏感与不敏感两种文件系统上都成立。
- **适用边界**：任何「上游 pkg-config 模块名与 conan 包名仅大小写不同」的包（`SDL_*` vs `sdl_*` 是 SDL 1.2 家族常态）；
  同族风险还包括 `ZLIB`/`zlib`、`OpenSSL`/`openssl` 之类拼写差异。

### 4.3 头文件第二拼写（编译阶段）
- **症状**：`font.c:22:10: fatal error: 'SDL_image.h' file not found`（`-I<sdl_image>/include` 在位却仍找不到）。
- **根因**：`sdl_image/sdl_mixer` 包头文件实际在 `include/SDL/` 下，而其 `cpp_info.includedirs` 是 `include`。
- **最终方案**：补发的 `.pc` 里 `Cflags` 同时给出 `<pkg>/include/SDL` 与 `<pkg>/include` 两种拼写
  （criticalmass 是先例，它靠手传 `SDL_CFLAGS` 达成同一效果）。

### 4.4 autoconf 2.69 的 `CONFIG_SHELL` 重执行 + HMDFS getcwd（configure 起手）
- **症状**：`shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty`
  → 一串 `job-working-directory:` errno 风暴 → `configure: error: working directory cannot be determined`。
- **根因**：CI profile `[buildenv]` 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`，该 bash 在 HMDFS 目录下
  `getcwd()` 失败；**autoconf 2.69 生成的 configure 只要 `CONFIG_SHELL` 非空就 `exec $CONFIG_SHELL` 重执行自身**
  （vor 的 configure 第 139/154 行实拍该块），所以 `sh configure` 也救不回来。
- **探针实拍**：同一 HMDFS 目录下 `/bin/sh` → `PWD=… ok`；`/data/service/hnp/bin/bash` → `PWD=` 空 + getcwd 报错。
- **最终方案**：build() 内以**命令级赋值**运行 configure：
  `CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "<src>/configure" <toolchain 参数>`。
  参数不自己重写，而是从 `conanbuild.conf` 读回（`AutotoolsToolchain` 与 `Autotools` helper 共用该文件），避免漂移。
  ⚠ 为什么不能用 `os.environ` 或配方 env 脚本：`conanbuild.sh` 的 source 顺序是
  toolchain → deps → **profile buildenv 最后**，profile 的值必然赢（与 libfec 草稿结论一致）。
- **出处**：`knowledge/drafts/libfec-1.0-26-gc5d935f-configshell-bash-getcwd-hmdfs.md`（修复形状）
  与 `knowledge/drafts/DRAFT-autoconf269-config-shell-unset-not-empty.md`（2.69/2.71 重执行块差异、
  「置空 ≠ 未设置」陷阱）。二者仍是 DRAFT，未见对应正式 E 条目 ⇒ 本窗按 DRAFT 采用并留此出处。

### 4.5 `config.status` 的 `umask 077` 临时目录（configure 收尾）
- **症状**：依赖检查全部 `yes` 之后 `./config.status[708]: can't create ./confRcFzkL/subs1.awk: Permission denied`
  → `config.status: error: could not setup config files machinery`。
- **根因**：HMDFS 上 autoconf 以 `umask 077` 建 `./confXXXXXX` 后写入被拒（同 criticalmass 记录的
  `confbCr3zr/subs1.awk: Permission denied`，属 E011/E129/E206/E223 同族）。
- **最终方案**：build() 前把**生成物** `configure` 里的 `umask 077` 就地放宽为 `umask 022`
  （configure 会把它写进生成的 config.status）。这是 criticalmass `_fix_umask_077` / cheops / pakchois
  已在用的构建期放宽，**不落 patches/**（不属源码修改，也不该被当作平台补丁审查）。

### 4.6 `make install` 路径翻倍（package 阶段）
- **症状**：`install: /storage/.../p/storage/.../p/bin/: No such file or directory`（前缀出现两次）。
- **根因**：本包 `--prefix` 必须是**包最终绝对目录**（见 §5），而 GNU autoconf 的安装规则拼的是
  `$(DESTDIR)$(bindir)`；再叠上 conan 默认的 `DESTDIR=<package_folder>` 就成了 `<pkg><pkg>/bin`。
- **最终方案**：`autotools.install(args=["DESTDIR=", "-j1"])` —— DESTDIR 留空，前缀本身已是目标绝对路径；
  同一条 args 里补 `-j1`（install 阶段一样会撞 HMDFS jobserver mkfifo：实测
  `make: jobserver mkfifo: ~/tmp/GMfifo10018: Operation not permitted`）。

### 4.7 本窗自己犯的、已修的账目错
- test.sh 第一版在"改名数据目录"分支里既 `TOTAL=$((TOTAL+1))` 又调 `check`，打出
  `ASSERTIONS=26 PASSED=25 FAILED=0` ⇒ 被自己的"必须 25 条"总闸拦下（`[result] FAIL`）。
  已改为统一由 `check()` 计数；**没有为了过门把 25 改成 26**，而是让断言数回到设计值。

## 5. 关键设计：`--prefix` = 包最终绝对目录

`Makefile.in` 有 `paths := -DDATA_PREFIX=\"$(pkgdatadir)\"`，`file.c:find_data_dir()` 的取数顺序是
`$VOR_DATA` → 相对 `data` → `DATA_PREFIX`。**conan 的 `AutotoolsToolchain` 默认 `prefix="/"`**，
照默认会把运行期数据路径焊死成 `/share/vor` ⇒ 装完即"找不到数据"。
本配方因此用 `AutotoolsToolchain(self, prefix=self.package_folder)`（实测 `conanbuild.conf` 回显
`--prefix=/storage/.../p`，`AutotoolsToolchain.generate()` 阶段 `self.package_folder` 可用）。
双保险：`package_info()` 另外用 `runenv_info` 导出上游自带的 `VOR_DATA` 钩子。

**代价与边界**：包因此不可 relocate（缓存路径被烧进二进制）——这是上游"游戏把 pkgdatadir 编进程序"的既有设计，
与 criticalmass 面对的是同一问题；conan 默认不搬迁包目录 ⇒ 成立。若日后需要可搬迁形态，
正道是给 `file.c` 增加安装前缀探测（属上游改动，需单独打补丁 + PR 说明），本窗未做。

## 6. 数据资产（PNG）打包口径

- 上游 `data/` 共 **61** 枚：59 PNG + `bang.wav` + `mph.xm`（`.pov`/`font_guts.c`/`povimg.sh` 是**资产生成器**，不参与构建）。
- `Makefile.in` 的 `install-data` 原生安装 `$(srcdir)/data/*.png|*.wav|*.xm` 到 `$(pkgdatadir)` ⇒
  **由 `make install` 打包，不在 `package()` 里手拷**（与 criticalmass 因 automake 不装 data 而手拷的情况不同）。
- ⚠ 风险点（本轮按实物复算过，规则链写死在这里，免得读者只 grep 一枚文件就误判）：
  `data` 目标 = `Makefile.in:77` 的 `data: $(graphics) build-dir-data-link`，而 `$(graphics)`
  （`Makefile.in:59-60`：ship/icon/life/font + rock00…rock49）的**再生规则不写在 `Makefile.in` 里**，
  由 `Makefile.in:116` 的 `include $(srcdir)/gfx.mk` 引入 —— `gfx.mk:2` 是
  `gfx-deps := gfx.mk povimg.sh`，`gfx.mk:4-25` 六条 `data/*.png` 规则**每一条**的 recipe 都是
  `./povimg.sh +W.. +H.. $< > $@`，而 `povimg.sh:3` 本体是
  `povray -D +A -O- +FP $* | pnmcrop | pnmtopng -transparent ...`。
  ⇒ PNG 规则**确实**依赖 `povimg.sh`，进而需要 `povray` + `netpbm`（B 机实测
  `command -v povray` 与 `command -v pnmtopng` 均 NOT FOUND）。
  ⚠ 取证陷阱：`grep -cE "povimg" Makefile.in` = **0**、`grep -cE "povimg" gfx.mk` = **7**——
  只看前者会得出"`Makefile.in` 无 `%.png` 规则 ⇒ 时间戳漂移时 `No rule to make target`"的错误结论；
  `include` 之后规则是齐的，真实后果仍是**重建 PNG 时缺 povray/netpbm 而失败**（`No rule to make
  target` 只在把 `gfx.mk` 一起丢掉时才成立）。
  tarball 内 PNG 与 `.pov`/`gfx.mk`/`povimg.sh` 同 mtime（2020-04-18 09:51）⇒ make 判定不需重建，
  实测整条构建链**没有**调用 povimg.sh（`make` 输出里只有 `test -e data || ln -s $(srcdir)/data`；
  实读行 = 随 PR 的 `reports/w3-local-ci.log:312` 与 `:320`，且 `grep -c povimg` 在
  `reports/conan-create.log` 与 `reports/w3-local-ci.log` 各为 **0** ⇒ "没调用" 是可核读数而非推断）。
  若某日 tarball 时间戳变化触发重建，会以"缺 povray / 缺 pnmtopng"失败——届时应做时间戳冻结
  （criticalmass `_freeze_autotools` 先例），**不要**引 povray 依赖。
  ⚙ 实物坐标：上列 `Makefile.in`/`gfx.mk`/`povimg.sh`/`INSTALL`/`configure.ac` 都在设备侧上游解包目录
  `~/tmp/ch/home-vor/p/voredd60360bd865/s/`（tarball sha256 见 §2）。`Makefile.in` 已按 sha256 登在随 PR 的
  `reports/failure-state-evidence.md` §0 的 S3；`gfx.mk`/`povimg.sh`/`INSTALL`/`configure.ac` 四件的本窗
  实算「字节 | 行数 | sha256」登在同件 **§11**，读者据此可判定自己手上的 tarball 是否同一份。
  六条 `data/*.png` 再生规则的实读行号 = `gfx.mk:4/7/10/13/16/24`（本窗 `grep -n "^data/" gfx.mk` 实拍）。
- 59 PNG 全部落 `share/vor/`（实测 `ls $P/share/vor/*.png | wc -l` = 59，总数 61）。

## 7. 五维测试账本（R51）

| 维度 | 读数 | 依据 |
|---|---|---|
| ① 上游测试**静态总数** | **0** | `grep -nE "check\|TESTS" Makefile.in` → 无输出；`.PHONY` 列表为 all/clean/maintainer-clean/install/uninstall/…（**无 check**）；`configure.ac` 无 `AC_CONFIG_TESTDIR`/`AM_INIT_AUTOMAKE`；源码树无 `tests/`、`test/` 目录 |
| ② 上游**注册可执行数** | **0** | 无任何注册入口可跑（`make check` 会直接 "No rule to make target 'check'"）⇒ 配方 build() 不发 check，属事实而非省略 |
| ③ **实测执行数** | 上游 0 / 消费者 **25 条断言全跑** | `test_package/test.sh` 末行 `ASSERTIONS=25 PASSED=25 FAILED=0`（conan create 的 test 阶段真实执行）。**随 PR 可核的实读位置**：`reports/conan-create.log:186` 与 `reports/w3-local-ci.log:436`（两处逐字相同，本窗 `grep -n ASSERTIONS` 复算各 1 命中）。探索期 4 轮 conan-verify 的日志在 §11（设备侧，不随 PR），4 枚内该串 0 命中 |
| ④ **跳过分类** | 上游：0 条（无测试可跳）；框架：**L2 / L4 / L5 各 1 条 =「⏭️ 跳过（无 cache 路径）」**（判决行写 PASS，实为未执行 ⇒ 本窗手工补齐等价证据，见 §8）；运行期：显示/音频**未跳过**，按能力实测如实记录（§8） | 逐字引文＝`reports/conan-verify-report.md:43`（L2，判决行 `:42`）、`:46`（L4，`:45`）、`:49`（L5，`:48`）——三行**同一串**，出自框架 `scripts/ohc/conan_verify.py:800/:851/:942`。⚠ 两条判决口径不同源，必须分开记：`reports/w3-local-ci.log:450-457` 是同一次本地 CI 的另一套读数（`L2_RESULT=skip: vor version/help failed`、`L4_RESULT=pass: patches clean`、`L5_RESULT=pass: bin/ has content`）⇒ 本表只取 conan-verify 那一套，w3 侧的 L4/L5 "pass" 不等于"检查真的做了" |
| ⑤ **失败数** | **0** | conan-verify `**Verdict**: PASS`；test.sh `FAILED=0` |

- **消费者断言数 = 25**，分三组（详表见 `test_package/MANIFEST.yml`）：
  CLI 面 11 条（`--version` 退出码与逐字 banner、`--help` 退出码 + 4 行 usage、未知短/长选项与裸参数的报错）；
  数据资产面 11 条（PNG 计数 59、总数 61、9 枚关键文件逐一存在）；
  运行期数据定位面 3 条（把包内 `share/vor` 改名 → 报 "Can't find VoR data!"；放回 → 不再报；无动态链接器错误）。
  - **计数口径先钉死：分组数 = `test.sh` 里 `check` 的实执行次数，不是编号个数**（编号只有 1–14，
    但 4 与 11 在循环里、12 的两个分支互斥）。本窗按 `check` 调用点复算：CLI 面 = 编号 1/2/3/5/6/7/8
    各 1 条（`test.sh:91/92/97/105/107/111/115` 七处）+ 编号 4 在 `test.sh:99` 的四枚 needle 循环里
    跑 4 次（`-f, --full-screen`｜`-s, --silent`｜`-V, --version`｜`-?, --help`，调用点 `:100`）= **11**；
    数据资产面 = 编号 9/10 各 1 条（`:121/:123`）+ 编号 11 在 `test.sh:125` 的九枚文件名片段循环里跑
    9 次（调用点 `:126`）= **11**；运行期数据定位面 = 编号 12（`:138` 与 `:142` 二选一，正常路径走
    `:142`）+ 编号 13（`:149`）+ 编号 14（`:151`）= **3**。11+11+3 = **25**，与 `test.sh:164` 的总闸
    `[ "$TOTAL" -ne 25 ]`、`MANIFEST.yml` 的三处 `assertions: 11/11/3`、同件 `:44` 的
    `assertion_count: 25`、`reports/conan-create.log:186` 与 `reports/w3-local-ci.log:436` 的
    `ASSERTIONS=25 PASSED=25 FAILED=0` **五处同源**。
  - **第三种数法一并钉死**：`test_package/conanfile.py:41` 的
    `assert os.path.isfile(binary), "vor binary missing at %s" % binary` 是跑 `test.sh` 前的
    **前置存在性守门**、在 `check` 之外 ⇒ 按 **`assert` 语句个数**数得 25+1=**26**，按本包口径
    （**`check` 实执行次数**，见上）得 **25**；两个数只差这一条守门断言，**台账一律取 25**
    （`manifest.yaml` 的 `added_consumer_assertions: 25`、`MANIFEST.yml:44` 的 `assertion_count: 25`、
    `test.sh:164` 总闸、`reports/conan-create.log:186`、`reports/w3-local-ci.log:436`）。
    ⚠ 它与 §4.7 被修掉的 `ASSERTIONS=26` **不是一回事**：那次是同一分支里既 `TOTAL+1` 又调 `check` 的
    双重计数（真实缺陷），已改回由 `check()` 单点计数，不是换了个口径。
    （顺带一枚坑：`grep -c assert test_package/conanfile.py` 得 **3**，多出的 `:9` 与 `:19` 是 docstring
    里的散文提及，真实 assert 语句只有 `:41` 一条。）
  - ⚠ 本轮改掉的一处自相矛盾：`MANIFEST.yml:31` 的 description 原先写「CLI 面 **8** 条」——8 是 CLI 面
    的**编号个数**、不是断言数，与紧接其下 `:33` 的 `assertions: 11` 打架，按旧值分组相加得
    8+11+3=**22** ≠ 25。现按上面的调用点复算把 description 定稿为 **11 条**；只动 description 文字，
    `test.sh` 本体与三处 `assertions:` 值均未动 ⇒ 没碰构建输入，W3 证据不受影响。
- **N_runner = 1**：实际执行断言的测试载体只有 `test_package/test.sh`（经 conan create 的 test 阶段驱动，
  由 `/bin/sh` 解释）。上游 runner 0 个；框架 L2/L4/L5 载体本轮为 skip ⇒ 不计入。
- **`upstream_test_in_build: false`** 的理由即 ①②，不是"忘了加 make check"。
- 测试面复核口径：本包**没有**为过门 disable 任何测试、没有缩分母、没有放宽断言、没有伪造日志或
  `.ci-result.json`（`.ci-result.json` 由 finish 写入，本窗未手工创建）。

## 8. 运行期能力实测（原样贴调用与输出）

在 conan 官方 run env 内（`conan install --requires=vor/0.5.8@ohpcd/stable -g VirtualRunEnv` + `. conanrun.sh`）执行；
裸 shell 直接跑包内二进制会因未注入 `LD_LIBRARY_PATH` 报
`Error loading shared library libSDL-1.2.so.0 …`（属环境未激活，不是产物缺陷，见 `~/tmp/uc2/z75v-vor/runenv/install.log`）。

| 调用 | 输出（原样） | 退出码 |
|---|---|---|
| `vor --version` | `Variations on Rockdodger 0.5.8` | 0 |
| `vor --help` | `Dodge the rocks until you die.` + usage | 1（上游设计：help 后 `return 0` ⇒ main 返回 1） |
| `SDL_VIDEODRIVER=none vor -s` | `vor: SDL error: 'none not available'` | 1（test.sh GUARD_RC 实录） |
| `SDL_VIDEODRIVER=none vor`（不传 `-s`，走音频） | `Can't open sound, starting without it` + `vor: SDL error: 'none not available'` | 同上 |
| `vor -s`（**不指定驱动**，2 秒看门狗） | 无错误输出；进程存活到被看门狗 SIGKILL | 137（`kill -9`） |
| 数据目录改名后 `SDL_VIDEODRIVER=none vor -s` | `Can't find VoR data! Tried:` 后逐条列出 `$VOR_DATA`(空) / `data` / `<pkg>/share/vor` | 1 |

**结论（可交付口径）**：
1. **视频**：本机（B 机，带会话）默认驱动下 vor **能进入主循环**（跑到看门狗计时才终止）⇒ 不是"只能编译"；
   强制不存在驱动时在视频层失败并给出 SDL 原文 `'none not available'`。
2. **音频**：`SDL_Init(SDL_INIT_VIDEO\|SDL_INIT_AUDIO)` 失败时上游自带降级为无声音继续
   （打印 `Can't open sound, starting without it`），叠加 §3 的 `sdl_mixer --disable-music-mod` ⇒
   **背景音乐 `mph.xm` 在本依赖组合下不可用**（依赖能力缺口，已披露，未藏）。
3. **ELF 真实性**：`bin/vor` 为 PIE（`Type: DYN`）、`GNU_STACK` 非可执行（NX）、有 `GNU_RELRO`；
   `NEEDED` = `libSDL-1.2.so.0 libtiff.so.6 libjpeg.so.62 libturbojpeg.so.0 libzstd.so.1 libwebp.so.7 libsharpyuv.so.0 libc.so`
   （SDL_image/SDL_mixer 静态链入 ⇒ 无对应 NEEDED）；含 `.codesign` 段（package() 自签产物）。
   ⇒ 这三项正是 L4 跳过时缺的等价证据。
4. CI worker 若无显示，本包 test_package 的断言**不依赖显示**（§7 三组断言都在 `--version/--help/选项错误/数据定位`
   路径上，视频探测统一 `SDL_VIDEODRIVER=none` + 20 秒看门狗 ⇒ 有显示也不会卡死、无显示也不会假绿）。

## 9. 交付物与核对

```
archives/v/vor/commands.json                     # 软件级（R38/L0k/PF8：type=tool，versions.ref=vor/0.5.8）
archives/v/vor/0.5.8/conanfile.py                # 配方（无补丁依赖）
archives/v/vor/0.5.8/conandata.yml               # 官方 URL 标量 + sha256（无 patches 键）
archives/v/vor/0.5.8/manifest.yaml               # 版本级（status: built，test_passed: 25/failed: 0）
archives/v/vor/0.5.8/notes.md                    # 本文件
archives/v/vor/0.5.8/test_package/conanfile.py   # 应用型（VirtualRunEnv + self.run）
archives/v/vor/0.5.8/test_package/test.sh        # 25 条断言（L0c 测试源文件）
archives/v/vor/0.5.8/test_package/MANIFEST.yml   # 上游 0 + 消费者 25 的声明与取证命令
archives/v/vor/0.5.8/reports/                    # conan-verify-report.md / conan-create.log /
                                                  # w3-local-ci.log / test-report.md /
                                                  # failure-state-evidence.md（§4.2 故障态读数的逐字摘录）/
                                                  # z75f-*（第 5 轮）+ z75q-*（第 6 轮）判决各两件 + pf7-source-equivalence-evidence.md（本窗 z75z）⇒ 共 10 枚
```
- `conan-init` 生成的**库模板**遗留 `test_package/CMakeLists.txt`、`test_package/test.c` 已移出工作树
  （存 `~/tmp/uc2/z75v-vor/removed-template/`）——它们是模板产物、且 `find_package(vor)` 对应用包不成立。
- 无 `patches/` 内容 ⇒ `patches/` 目录为空（未提交空目录内容）。
- ⚠ `packaging/` 缺（本窗按框架自己的判据复算，不是猜）：`scripts/ohc/submission.py:209-217` 的
  `_check_packaging_present(ver_dir, status)` 对 `status` 为 `built`/`published` 的包要求
  `packaging/*.tar.gz`；本包版本级 `manifest.yaml` 的 `status: built` ⇒ 直接调用该函数得
  **`packaging_present=False`**。同批复算的其余五项：`manifest_complete=True`、`progress_closed=True`、
  `patches_valid=True`、`no_temp_files=True`、`test_report_present=True`（`submission.py:1073-1085`
  的 checklist 就是这六项）。
  处置口径：这道自检属于 `ohc-run.py submit`，**`$P run` 的链路（finish→W3→W4→提交→推送→建 PR→CI）不进它**；
  而补 `packaging/` 要重新出一遍包 ≡ 动构建侧、作废 W3 证据 ⇒ 本轮**不补**，只把"若日后要 submit，
  先中和本条"写在这里，避免后窗把它当成新问题重查一遍。
- ⚠ `reports/` 五件此前被仓根 `.gitignore:96` 的 `reports/` 规则整目录挡住、**根本不在版本库里** ⇒
  notes 里所有「随 PR 可核」的 `reports/*.log:NNN` 指针在被 add -f 之前都解析不了。整改提交
  `248c10f9ae` 用 `git add -f -- <精确路径>` 逐件收进 PR（`conan-create.log`/`conan-verify-report.md`/
  `w3-local-ci.log`/`test-report.md`/`failure-state-evidence.md`）；`reports/audit-result.json`
  **故意不随 PR**——它是**第 3 轮**整改的输入（`verdict: fail`、P1×2/P2×3/P3×5），随 PR 反而与整改后的正文
  相互打脸；W4 需由主窗/CIW 对整改后的 HEAD **重跑**，不能拿这份旧的冒充。
- **随 PR 的 reports 现共 10 枚**（`git ls-files archives/v/vor/0.5.8/reports/ | wc -l` = 10，本窗 z75z 现算；z75f 棒当时是 **7 枚**，故下面 :316-318 的「五件 + 第 5 轮两件」还要再加第 6 轮判决两件与本窗那件取证件，逐件与 sha256 见 §13）：
  上面五件 + **第 5 轮**只读重审（审计件 z75f，判决对象 = HEAD `acedf9f823`）的两件判决件
  `z75f-audit-result.json`（add -f 当时实算 sha256 `e79d973574206339aeb6d13b914de8389e585b20e385dcca17581945494008e3`、
  `verdict: fail`、P1×1/P2×1/P3×3）与 `z75f-w4-report.log`（sha256 `bd116ffb581f993b5cd0f7e810a6ebbedb8b3bb7695bcfe840345f4f08615448`），
  同为 `git add -f -- <精确路径>` 逐件收进。⚠ 这与上一行排除 `audit-result.json` **不矛盾**：第 3 轮那份
  已被其后的整改提交逐条闭环、留在 PR 里才与正文打脸；第 5 轮这两份是**当前 HEAD 的最新判决原文**，
  随 PR 后读者不必碰任何设备侧路径就能看到「判了什么、本棒闭了哪几条」——本棒闭 1 P1 + 1 P2 + 2 P3，
  第 5 条 P3（`DELIVERY-INCOMPLETE`）记的是「尚无 PR」这一台账状态，建 PR 属主窗分工、本棒不代做。

## 10. 路径 B 声明（判定 **create**：草稿已落盘、Issue 已建，本节是交付口径）

- **适配路径**：路径 A（预生成 configure 的标准 autotools 配方）+ 路径 B（**create**，新机制 1 条，见下两行）。
- **使用知识库**：`DRAFT libfec-…-configshell-bash-getcwd-hmdfs`（§4.4 修复形状，已采用）、
  `DRAFT-autoconf269-config-shell-unset-not-empty`（§4.4 机制解释，已采用）、
  E011/E129/E206/E223 同族的 HMDFS `umask 077` 结论（§4.5，criticalmass 先例落地）、
  criticalmass 1.0.2 配方（§4.3 头文件双拼写、§5 数据前缀问题域、自签与 -j1）；
  G2 失败时引擎命中过 **E490 / E540 / E317**——E490 为提示未触发（tarball 权限完好），
  E540、E317 是**误配**（其方案与本案症状无关），本窗未据其改动，仅如实记录。
- **知识库扩展**：是——新机制 1 条（草稿实际条数 **1**，与本行一致）：
  **「HMDFS 大小写不敏感 + pkg-config 按文件名且大小写匹配」的组合会把"仅 `Requires:` 前转的别名 .pc"
  变成覆盖真身的自引用文件，表现为 configure 报 yes、`pkg_cv_*` 却为空、最终只在链接期爆
  undefined symbol；正确做法是按原 `.pc` 内容改写副本（`pkg-config --debug` 的
  `already in requires chain, skipping` 是定位指纹）」（§4.2）。
  - 补证与收紧（不改写上面的结论，只补口径）：本窗在 B 机复算该指纹时实测
    `already in requires chain, skipping` **单独不是判据**——传递链上的正常重访也会打印它
    （真身 .pc 集合下该行为 9 条）。**可用的判别式是 `Searching for 'X' requirement 'X'`
    这一同名对 + 返回值为空**。复算读数见草稿的 `verification_cmd`。
  - 该 `verification_cmd` 的**读数方差必须一并写死**（草稿的 `verification_cmd` 现已收成**单行可执行**，
    期望读数与三个探针坑迁到同 stem 的 `.md`）：本窗用自己的私有工作目录
    `~/tmp/uc2/z75x-vor-fix/kc-pc-alias` 连跑两次，输出逐字节相同（11 行，sha256
    `7906fba85918cab139cbee9011dcc475a1a3d394f14233f0396266a72b1b54f4`，
    摘录见 `reports/failure-state-evidence.md:247-257`），读数为
    `A_unique_inodes=1 / A_dir_entries=foo.pc / A_libs=[] / B_libs=[-lfoo_real]`；
    而**同一台 B 机换一处目录**实测出现过 `A_unique_inodes=2 / A_dir_entries="foo.pc Foo.pc"`
    且修复态三值全空 ⇒ **稳定判据只有「`A_libs` 为空 + `--debug` 里的同名对」这一条**，
    inode 数与目录项计数受 HMDFS 目录状态影响，不得当判据用。
  - 整改二棒（同属主理-75，写入区 `~/tmp/uc2/z75r-vor-fix2/`）复算并复核了上面这段：
    ①本仓解析器 `scripts/ohc/models.py:72` 的 `parse_kv_file` 对该 `.kv` 得 **41 个键**，取出的
    `verification_cmd` = **1199 字节 / 1 行**（无续行、尾部无悬空 `-`）⇒ 折叠确实已经拆掉；
    ②把该串**原样**交给 sh 在本棒私有目录连跑两次，两次输出逐字节相同（11 行 / 284 B /
    sha256 与上一棒同值 `7906fba85918cab139cbee9011dcc475a1a3d394f14233f0396266a72b1b54f4`）、
    `VC_RC=0`，读数同上（`A_unique_inodes=1 / A_dir_entries=foo.pc / A_libs=[] / B_libs=[-lfoo_real]`）
    ⇒ "单行可执行" 与 "两处私有目录同一读数" 都是实测，不是推断；逐字命令体与输出见
    `reports/failure-state-evidence.md` §10；
    ③草稿 `rec_command` 的 `--build=missing` 已在位、解析出的值尾部是 `-pr:b=…ohos-aarch64`（无悬空 `-`）。
    ⚠ 该探针命令自带 `rm -rf $d` + `mkdir -p $d` ⇒ `d=` 换成任一可写私有目录都成立，但**不要**把它指回
    别的棒的目录（那会删掉别人的现场）。
- **草稿实存（与上面三行互证，同 stem 成对，均在仓根 `knowledge/drafts/`）**：
  `knowledge/drafts/DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference.kv` 与
  `knowledge/drafts/DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference.md`。
  配方落地点：`archives/v/vor/0.5.8/conanfile.py:68-72`（别名表）与 `:111-153`
  （`_write_pkgconfig_aliases`，docstring `:124-130` 记本机制）——读者可在 PR diff 内逐条对上。
- **关联 Issue**：**#3502** — https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3502
  （由主窗建立；本窗按分工不碰平台，故只回填实号与链接，未做平台侧回读）。
- **PR 前缀**：`【知识库扩展】`（最新 B判定=create ⇒ 标题须用该前缀）。
- **判 create 的依据（hit 四条件不成立，层次差指到行号）**：
  - **E193** `knowledge/doc/E193.md:14-21` 的根因段只陈述"仅大小写不同的文件名指向同一 inode"
    这一平台属性，其 `:23-27` 推荐方案是 `skip-case-sensitive-tests`——处方落在**测试期**
    （跳过大小写敏感测试用例）；本条处方落在**构建期**（不造 `.pc` 大小写别名、按原内容改写副本）。
    根因半边重叠、解法不同层 ⇒ 不算覆盖。
  - **E075** `knowledge/doc/E075.md:14-20` 的根因是 `C_INCLUDE_PATH` 让 pkg-config 过滤掉 `-I`
    （环境变量层，且只影响 `--cflags`），`:22-34` 处方是 unset 两个变量；本包 `--cflags` 与
    `--libs` 双双为空、unset 后仍为空 ⇒ 症状同族但根因与处方均不同层。
  - 另在草稿 `similar_to` 里交代了 **E247**（`--static` 与 `Libs.private` 字段内容缺失，
    `knowledge/doc/E247.md:14-20`）与 **E004/E015**（undefined symbol 族，无 pkg-config 元数据层）
    为什么也不算覆盖。
  - **最锋利的判别式**：`grep -rilE "already in requires chain" knowledge/` 在本条落盘前
    **全库 0 命中**（正式库 540 条 + 池内 2922 份件皆无；两枚库计数本窗 z75z 现算 = 540 / 2922 ✓）。⚠ 同一条 grep 在**当前 HEAD** 上复算 = **2** 枚命中，即本条草稿自身那一对（`knowledge/drafts/DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference.kv` 与 `.md`）⇒「落盘前 0 命中」是反事实读数，读者照抄该命令应以 2 为准。
  - `draft-review` 三态建议 = **create**（TOP 相似 E247 0.15 / E075 0.11 / E193 0.10，
    全部低于 0.30 灰区线；`knowledge_check` RC=0）。

## 11. 日志与断点（设备侧绝对路径，B 机）

```
~/tmp/uc2/z75v-vor/evidence-01-analysis.md        # 文档阅读 + 上游剖析
~/tmp/uc2/z75v-vor/evidence-02-env-deps.md        # 构建准入 / W0 依赖实测 / 两个环境地雷
~/tmp/uc2/z75v-vor/evidence-03-build-fail.md      # 模式 A 失败读数与根因
~/tmp/uc2/z75v-vor/gate1-preflight-before.log     # 门禁 1（写 requires 前）
~/tmp/uc2/z75v-vor/gate1b-dep-recipes.log         # conan download --only-recipe（R35）
~/tmp/uc2/z75v-vor/gate1b-sdl-binary.log          # --build=never 二进制命中实录
~/tmp/uc2/z75v-vor/gate1-recipe-search.log        # 门禁 2
~/tmp/uc2/z75v-vor/gate2-init-build*.log          # init-build
~/tmp/uc2/z75v-vor/gate3-build.log                # 门禁 3（模式 A 14 步，失败）
~/tmp/uc2/z75v-vor/gate3b-conan-init.log          # 首稿生成
~/tmp/uc2/z75v-vor/gate4-conan-verify.log         # 门禁 4 第 1 轮（1579 B, 03:38）G2 FAIL
~/tmp/uc2/z75v-vor/gate4-conan-verify-2.log       # 门禁 4 第 2 轮（1579 B, 03:43）G2 FAIL
~/tmp/uc2/z75v-vor/gate4-conan-verify-3.log       # 门禁 4 第 3 轮（1579 B, 03:46）G2 FAIL
~/tmp/uc2/z75v-vor/gate4-conan-verify-.log        # 门禁 4 第 4 轮（1281 B, 03:57）G2/G3 PASS
                                                 #   ↑ 文件名尾部就是**一枚孤立的连字符**，不是省略号
~/tmp/uc2/z75v-vor/pc-probe/                      # PkgConfigDeps 实物 .pc 快照
~/tmp/uc2/z75v-vor/runenv/                        # 运行期证据采集环境
~/tmp/ch/home-vor/p/b/vor421b198eeb77c/b/build-release/   # 故障态一轮的 config.log + Makefile
~/tmp/ch/home-vor/p/b/vor9bd94de5632d0/b/build-release/   # 修复态最后一轮（04:04）同名两件
~/tmp/uc2/z75q-vor/probe-real-pcset.log           # pkg-config --debug 真实生成集实拍（兄弟棒落盘）
~/tmp/uc2/z75q-vor/selfcheck-pc-alias.log         # 同上，自造最小复现
~/qzy/主理-75-vor-0.5.8/archives/v/vor/0.5.8/reports/   # conan-verify-report.md + conan-create.log
                                                 #   + w3-local-ci.log + test-report.md
                                                 #   + failure-state-evidence.md（随 PR 的故障态摘录）
                                                 #   + z75f-audit-result.json + z75f-w4-report.log（第 5 轮 W4 判决件，
                                                 #   随本棒整改提交 add -f 入库；此后第 6 轮判决两件（z75q）与本窗取证件一件同批 add -f ⇒ 共 10 枚）
                                                 #   ⚠ 前 5 件自 248c10f9ae 起已在版本库里（此前被 .gitignore 的 reports/
                                                 #   规则挡住）⇒ 上面各节写的「随 PR 可核」从该提交起才成立；本目录只是
                                                 #   同一批件的设备侧原件。第 3 轮的 audit-result.json 仍未随 PR（见 §9）；
                                                 #   本棒补进第 5 轮的两件判决件 ⇒ 当时 7 枚；本窗 z75z 现算 = 10 枚（逐件与 sha256 见 §13）。
```

⚠ **§11 更正（2026-09-27 整改）**：本节原先写 `gate4-conan-verify-{1..7}.log` 并称「第 7 轮全绿」，
设备侧该目录**实际只有上面 4 枚**（`ls` 复算：`gate4-conan-verify.log`、`-2`、`-3`、`-`），
不存在 `-7`，也没有 1..7 序列；轮次计数已删除。**最终全绿轮次的判决件是随 PR 的**
`reports/conan-verify-report.md`（`**Verdict**: PASS`、`**Date**: 2026-09-27T04:03:33.553417`，
与该包 `.conan-verified` 的 `verified_at=2026-09-27T04:03:33.554469` 同刻）与
`reports/conan-create.log`——上列 4 枚探索日志里 `undefined symbol`/`pkg_cv` 命中数**全为 0**，
不要拿它们当故障态或全绿的凭据。

## 12. 环境备注（他窗/后续窗口会撞上，先记录）

1. `CONAN_HOME=$HOME/tmp/ch/home-vor` 从 `home-B-cwalk` 复制配置层时，**`home-B-cwalk` 没有 `profiles/` 目录**
   ⇒ 配方/profile 一律用仓内 `ci/conan/profiles/ohos-aarch64`。
2. **B 机 `~/usr/local/bin/automake` 的 shebang 指向不存在的 `~/usr/local/bin/perl`** ⇒
   任何调用 ohc-run.py 且 PATH 含 `~/usr/local/bin` 的窗口都会在
   `scripts/ohc/check_env.py:33`（`str(e)` 未绑定的已知假红）处抛 `NameError`，
   并**在写出 `.build-context-*` 之前**中断 init-build。不碰框架、不碰共享目录的规避法：
   `PATH=$HOME/.local/bin:$HOME/.harmonybrew/bin:/data/service/hnp/bin:/usr/bin:/bin`
   （注意 `python3` 真身在 `~/.harmonybrew/bin`，不在 `~/usr/local/bin`）。
3. 模式 A 驱动（`ohc-run.py build`）的探索段**不使用 conan env** ⇒ 对本类包结构性不可用；
   它的 auto-retry 还观察到把重试命令串当 configure/make 参数传入
   （`configure: error: unrecognized option: '-fsSL'`、`make: sSL: No such file or directory`）。
   本窗按 R14 转手动/配方路线，未改框架。
4. 该 auto-retry 顺带在 `~/usr/local/bin` 装了 coreutils 9.10（新增 `ginstall`，2026-09-27 03:24）；
   本窗未回滚（共享目录 = 用户资产），如需清理请主窗决定。
5. `AC_PROG_INSTALL` 在 conan buildenv 下选中了 `~/usr/local/bin/ginstall -c`（第 4 条的产物）。
   CI worker 上若无 ginstall，会回落到 `/bin/install`（本窗实测存在）或 tarball 自带的 `install-sh`，
   因此**配方不写死 INSTALL 覆盖**（避免把设备私装状态带进 CI）。
6. **软件级 `archives/v/vor/manifest.yaml`：本窗实测后决定不建**（免得下一窗又去"补齐三件套"）。读数：
   ①`ls -d archives/*/*/ | wc -l` = **6740** 个软件目录，其中带软件级 `manifest.yaml` 的 = **3872**
   （约 57%，**不是**硬惯例），版本级 `archives/*/*/*/manifest.yaml` = **7467**；
   ②与本包同形的应用型先例是分裂的——`archives/c/criticalmass`（同 SDL 1.2 家族，软件级只有
   `commands.json`）与 `archives/a/abook` **都没有**软件级 manifest，`abduco`/`lolcat`/`mc` 有，
   `sdl_image`/`sdl_mixer` 有、`sdl12-compat`/`cwalk` 没有；③R38/L0k/PF8 要求的软件级
   `commands.json` 已在位、全部构建事实也已在版本级 `manifest.yaml` 里 ⇒ 新建它拿不到任何新的可核读数。
   ⚠ 另记一条一手复算（框架侧缺陷，不是本 PR 的阻塞项）：`scripts/ohc/preflight.py:559` 的
   `check_branch_and_paths`（PF9，被 :639 调用）里 `bad = [f for f in arch if len(f.split("/")) < 5]`
   把**任何四段归档路径**判成"缺版本目录层"。本窗把该函数直接跑在本分支的 15 枚变更文件上，命中 1 条：
   `PF9 分支/路径闸: 变更路径缺版本目录层……CI 将报 No packages to build（490 例）:
   archives/v/vor/commands.json`——**这条今天就已经成立**（`commands.json` 本身是四段路径），
   与本包有没有软件级 `manifest.yaml` 无关，所以"补软件级三件套"既不会引入也不会解除该误报。
   对照实测：`bash ci/scripts/preflight_check.sh vor/0.5.8` 在临时放入一份软件级 `manifest.yaml`
   前后输出**逐字节相同**、RC 均为 0（该入口只跑依赖发布态与 R37 版本占用，不跑 PF9 路径闸）；
   临时文件已当场删除，工作树未留痕。
7. `MANIFEST.yml` 的 `assertions:` 三值与 description 的「几条」是两个口径（**编号个数** vs **实执行
   次数**），本包踩过了：编号只有 1–14，但 4/11 两个编号在循环里、12 的两个分支互斥 ⇒ 实执行 25 条。
   写声明时按调用点复算，别拿编号当断言数（详见 §7）。

## 13. PF7 例外链后半段（本窗 z75z 现取，随 PR 证据件 + 件数同步）

> 第 6 轮 W4 判决件（`reports/z75q-audit-result.json:22` 起，rule_id
> `PF7/R39-SOURCE-URL-NOT-OFFICIAL`，定级 **P1**）判本包取源披露只随 PR 了**前半段**：「作者站没有可直取
> 的发布物」在 `notes.md:40-41`、`manifest.yaml:28-31`、`conandata.yml:5-15` 三处可见，但
> **「为什么不能改用上游 GitHub 的 tag 件」这一半在正文与草稿里逐件 0 命中**（`codeload` / `99326` /
> `491131` 三串，本窗复算全 0，只有判决件自身各 1 命中＝叙述不是取证）。后半段现已落成随 PR 的一件并
> 挂进 §2 第 43 行：**`archives/v/vor/0.5.8/reports/pf7-source-equivalence-evidence.md`**
> （291 行 / 18627 字节 / sha256 `aa4054bf61b31845f40ee2c3c6998407da00ced53433c46468792ddbe929d686`；
> 节内行号：§0 读数一览 `:22-38`、§1 两枚 URL 实测 `:39-67`、§2 两树逐字节对账 `:68-105`、
> §3 tag 件缺件 `:106-135`、§4 `Makefile.am` 计数 `:136-146`、§5 缺 54 枚 PNG 与再生工具链
> `:147-178`、§6 作者站与 releases API `:179-236`、§7 后果链 `:237-277`、§8 复算坐标 `:278-291`）。
>
> 关键现取读数（复算命令全部抄在那件里，本窗不转述他棒数字）：Debian pool `.orig` = HTTP 200 /
> **361789 B** / sha256 与 `conandata.yml:19` 逐字同值；`codeload.github.com/JasonWoof/vor/tar.gz/refs/tags/0.5.8`
> = HTTP 200 / **99326 B** / sha256 `491131666a4a614d…`；两树常规文件 112 vs 52、共同 **51** 枚逐字节相同
> （`diff -rq` 输出 58 行、`grep -c differ` = **0**，正对照 `differ|Only in` = 58；另逐枚 sha256 独立比对
> 不匹配 **0** 枚），但 tag 件**缺**预生成 `configure`（`.orig` 侧实测 166325 B、`# Generated by GNU
> Autoconf 2.69 for VoR 0.5.8.`，与 §1 表 :22 对齐）、`aclocal.m4`、`autom4te.cache/`（目录 1 枚内含 5 枚
> 文件 ⇒ 第 6 轮报「无法从清单证实」那项本窗改走 `-type d` + `diff -rq` 第 3 行两种口径，已可证）与
> **54** 枚运行期 PNG；`Makefile.am` 递归计数两侧均 **0**（与 §1 :30 一致 ⇒ automake 自举路无输入）；
> `command -v povray` / `pnmtopng` / `pnmcrop` 在 B 机**均 NOT FOUND**（与 §6 :190-191 同口径）。
> ⇒ 换源**不等价**且不存在可用路径 ⇒ PF7 只能走例外披露，⛔ 不改 `conandata.yml:18` 的 `url`
> （改 url ⇒ recipe revision 变 ⇒ `conan create` / conan-verify / W3 全套证据作废）。
> 同窗把 §2 的旧口径「三条候选路径实测均只返回 1535 字节」改写为现取口径：那张 catch-all 是回显请求路径的
> wiki 创建页 ⇒ 与 `vor-0.5.8.tar.gz` 等长者恰为 1535 字节、同族页 1502–1550 字节、真主页 8591 字节。
>
> **件数同步**：`git ls-files archives/v/vor/0.5.8/reports/ | wc -l` 本窗现算 = **10**（§9 :315 与 §11 :418
> 原先的 7 枚是 z75f 轮读数，已在原处标注现值）＝ §9 登记的五件 + `z75f-audit-result.json`
> （sha256 前 16 位 `e79d973574206339`，与 §9 :317 登记值一致）+ `z75f-w4-report.log`（`bd116ffb581f993b`）
> + `z75q-audit-result.json`（`2ce62718b59c058c`）+ `z75q-w4-report.log`（`f4efb5cb32100098`）+ 上面那件
> 取证件；第 3 轮的 `reports/audit-result.json` 仍按 §9 的口径**不入库**。
---

**编译结束**: 2026-09-27 04:03
**最终状态**: built
