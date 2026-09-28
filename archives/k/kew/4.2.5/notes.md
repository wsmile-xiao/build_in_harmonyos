# kew 4.2.5 — HarmonyOS PC 适配记录

任务号 7801 · 分支 `feat/kew-4.2.5` · 构建主机 = B 机 · worktree `~/qzy/主理-74-kew-4.2.5`（基线 HEAD `48d9cee684`）

- 编译状态：通过。`conan create archives/k/kew/4.2.5 --user=ohpcd --channel=stable --build=missing -pr:h=-pr:b=ci/conan/profiles/ohos-aarch64` 退出码 0（槽位经 `build-slot.sh --kind short --mem 2500` 分配，收尾打印 `SLOT_DONE:ok MemAvailable=5812MB`）；构建日志 `~/tmp/uc2/z74-kew/create-8.log`，`sha256=3cd8f1549208f82d8f721d233f072fc07b43321f03c50ee61add01fbf1a0def4`。
- 测试状态：通过。消费者测试 36 条断言全绿，汇总行 `SUMMARY kew consumer: total=36 passed=36 failed=0`（日志内 `PASS ` 行实点 36、`FAIL ` 行 0）。上游测试清点：**分母 0、可用 0**；`find . -iname '*test*'` 命中 2 枚，但两枚都是文档页（`pages/testimonials.html`、`website/site_src/testimonials.md`），按判据**不计入分母**。判据：分母 = 可注册/可执行的上游用例数（`tests/` 目录数 + Makefile 的 `check`/`test` 目标数 + `ctest`/`add_test` 注册数），仅名字命中的文档页不是用例。清点命令与逐字段读数见 `test_package/MANIFEST.yml` 的 `upstream_test_census`（denominator 0 / usable 0 / find_matches_non_test 2）。未放宽任何判据、未跳过任何断言。
- 运行状态：部分可行（播放主流程在本机结构性不可行，见下）。**消费者测试内实测**（`test_package/test_kew.py:207-224`：起子进程前把 `LD_LIBRARY_PATH` 经 argv 注入到被测二进制，机理见适配点 10）：`kew --version` 退出码 0 且输出含 `kew version: v4.2.5`；`kew --help` 退出码 0，输出逐字为 `Run man kew for help.`（两份日志的 EVIDENCE 行逐字相同：`reports/conan-create.log:219`、`reports/w3-local-ci.log:515`）。⚠ 同一对参数在 **harness 的裸跑形态**下是失败的：`ci/conan/build_and_test.sh:1676-1697` 的 L2 smoke 用 `timeout 15 "$bin_file" --version` 裸跑、不注入 conan run env ⇒ musl loader 取不到 DT_NEEDED 里的 glib/chafa 等 ⇒ 本地 W3 档 `L2_RESULT=skip`（见第 4b 节）。⇒ 准确口径是「注入 run env 后 CLI 自检可用、裸跑不可用」：**既不得写成「kew 不能跑」，也不得写成「退出码 0 所以 CI 的 L2 会过」**。播放入口需要终端输入与声卡：B 机 `ls /dev/snd` 报 `Permission denied`，`find /system /vendor -name 'libasound*'` 命中 0 枚（miniaudio 的 ALSA 后端在编译期不需要头文件，运行期靠 `dlopen("libasound.so.2")`，因此链接能过、取不到设备）。程序在"Music Library 选择"提示处打印 `Error reading input.` 后退出码 0。⇒ 本包只申报"可执行文件在位、能完成自检式 CLI、并在使用声卡/终端之前就报出可识别失败"，**不声称能出声**。

## W0 依赖实证

口径：每个精确 requires 都跑 `conan install --requires=<name>/<ver> --build=never -pr:h=<wt>/ci/conan/profiles/ohos-aarch64 -pr:b=<同一份>`（`CONAN_HOME=~/tmp/ch/home-kew`），判据是日志同时出现 `Downloading binary packages` 与 `Install finished successfully` 且 rc=0；未使用通配 `conan list`。12 枚全部 rc=0：
`glib/2.84.0.1`、`chafa/1.18.2`、`fftw3f/3.3.10`、`opus/1.5.2.1`、`opusfile/0.12`、`libvorbis/1.3.7`、`libogg/1.3.5`、`libogg/1.3.6`、`taglib/1.13.1`、`zlib/1.3.1.1`、`zlib/1.3.1`、`pkgconf/3.0.6`；收口前补测 `proxy-libintl/0.5` 亦 rc=0。

- `fftw3f` 取的是**独立包 `fftw3f/3.3.10`**（其 `package_info` 里 `pkg_config_name = "fftw3f"`），不是 `fftw/3.3.11`（那个只给 `fftw3` 双精度名）。这条是按读配方确认的，不是按包名相似取用的。
- `taglib` 取 `1.13.1` 而非 `2.3`：`src/loader/tagLibWrapper.cpp` 与 `src/loader/lyrics.cpp` 用的是 `TagLib::String(value, TagLib::String::UTF8)` 与 `Ogg::XiphComment::fieldListMap()`，属 TagLib 1.x API 面。
- `faad2` 不需要：本仓 `archives/f/faad2/2.11.2` 实有 `PROGRESS.md`、`README.md`、`_meta.yaml`、`manifest.yaml` 四件，**没有 conanfile.py** ⇒ 定性为 **`faad2 本仓未适配（归档目录无 conanfile.py，制品仓取不到可用配方）`**。**口径订正（W4 r1 K6）**：配方注释 `conanfile.py:27` 写的 `no faad2 conan package is published` 把推断写成了事实。审计 r1 判决件的取证（issues[K6].evidence_output；制品仓查询，本窗按预算纪律未复跑）：`conan download faad2/2.11.2 -r=ohpcd --only-recipe` 返回服务端 `error:system acceleration policy not enabled`，**不是 `not found`**，不足以支撑「未发布」；该注释因改动会翻 rrev（作废已绑定的 W3 证据锚）故本笔不改，以本段为准。但 Makefile 第 68–103 行的 faad2 探测是可选特性（`make USE_FAAD=0` 即整块跳过），故按"关掉可选特性"处理，未因此 `$P block`。
- `gdk-pixbuf-2.0` 不需要：Makefile 第 115–119 行把它放在 `ifeq ($(UNAME_S),Darwin)` 分支里，非 Darwin 的 `PKG_LIBS` 不含它。
- 版本仲裁（图内已有硬冲突，两处 `override=True`，均取"另一分支已经解析到的那枚"以免多拉一次源码构建）：`libogg` 被 `opusfile/0.12` 钉 1.3.5、被 `libvorbis/1.3.7` 钉 1.3.6；`zlib` 被 `glib/2.84.0.1` 钉 1.3.1.1、被 `taglib/1.13.1` 钉 1.3.1。同仓先例见 `archives/a/abiword-plugin-docbook/3.0.8/conanfile.py`（注释明确要求统一到 1.3.1.1）。
- 副作用如实记录：`libogg` 取 1.3.6 会让 `opusfile/0.12` 的 package_id 与已发布制品错开，`conan create` 因此**从源码重建了 opusfile**（其余 10 枚均 `Already installed`）。该源码重建在本机已实测成功。

## 货源与哈希

取源 `https://github.com/ravachol/kew/archive/refs/tags/v4.2.5.tar.gz`。**5 次成功采样**（直连 codeload、经 ghfast 镜像、经 github.com 302 三种路径混合）全部 `12573259 B`、`sha256=a17f4acd54c78511bb14fc4e02aaaafc351f640388c3d29254f4397edfdc16a1`；另有 6 次纯 github.com 直连采样在 `codeload.github.com` 上 rc=28/52 超时或空响应（Windows 侧与 B 机侧都实拍到），所以哈希只按成功的 5 次定档。台账里的 Debian 池件是 **3.2.0+ds**，与本任务版本不同源，其语言/文件数/依赖数字一律未引用。

**托管地说明（W4 r1 K8，免得按 R39 追问）**：上游主仓是 `https://codeberg.org/ravachol/kew`（`conanfile.py:102` 的 `homepage`），GitHub 侧的 `ravachol/kew` 是**同名镜像**；取源走该镜像的 tag 归档件 `archive/refs/tags/v4.2.5.tar.gz`，字节与官方一致——哈希由收口轮自算 3 次采样确认（第 1 节，本窗沿用其实测读数），PF7 分类器对官方 github tag 址返回 None（判 CLEAN）。

实物普查（**统一按整棵 tarball 树**；解包件 `~/tmp/uc2/z74-kew/census/kew-4.2.5`，W4 r1 整改轮以 `find . -name '*.<ext>' -type f | wc -l` 同一口径复算）：`.c` **55**、`.h` **73**、`.cpp` 2、`.m` 1（macOS 专用，非 Darwin 分支不参与编译）。旧稿把 `src/` 子树的 `.c` 50 与整树的 `.h` 73 混写进同一句；本轮复算确认拆分为 `src/` 50 枚 + `include/` 5 枚 = 55（`.h` 的 `src/` 子树计数是 60），故一律取整树口径。⇒ 语言判 C 主体 + 一个 C++ TagLib wrapper，构建系统 = 裸 Makefile（无 configure/CMakeLists/Meson，主窗已一手定性，本轮复核一致）。

## 本地绿跑与交付态的取源地址分档（如实披露）

B 机对 `codeload.github.com` 不可达（`curl -L` 实测 rc=28/52，直连 `github.com` 只拿到 302）。因此 **W3/`conan-verify`/`finish` 的绿跑是在把 `conandata.yml` 的 url 临时换成 `https://ghfast.top/https://github.com/ravachol/kew/archive/refs/tags/v4.2.5.tar.gz` 之后完成的**（sha256 未改，镜像回的字节数与哈希与官方址逐字节相同）。收口时 `conandata.yml` 已按"备份 + 还原"改回官方址，`grep -n "url:" archives/k/kew/4.2.5/conandata.yml` 的读数见本文末「编译结束」块。
⇒ **绿跑 RREV 与交付 RREV 不是同一枚**（url 属配方内容）。两档分别记录在「编译结束」块，不得当作同一修订引用。

## 适配点（照既有处方，未自创姿势）

1. **E392（raw makefile 三坑）三条全部按条目处方处理**：`get()` 显式带 `filename="kew-4.2.5.tar.gz"`；`tools.build:compiler_executables` 用 `check_type=dict` 整体取字典再 `.get("c")/.get("cpp")`（不做 `$(origin)` 猜测、不裸用 shell `$CC`，同 R33）；`make` 一律 `cwd=self.source_folder`。
2. **`CC`/`CXX` 必须走 make 命令行**：Makefile 第 220–222 行有 `ifeq ($(origin CC),default) CC := gcc`，而 B 机没有 `gcc`（实测 `ls /data/service/hnp/bin/gcc` = No such file）。
3. **`UNAME_S=Linux` 显式覆盖**：`uname -s` 在本机返回 `HarmonyOS`（`uname -a` = `HarmonyOS localhost HongMeng Kernel 1.12.0 ... aarch64 GNU/Linux`），Makefile 第 171 行的 Linux 分支不命中 ⇒ `-fPIE/-pie/-Wl,-z,relro/-Wl,-z,now` 会被静默丢掉。目标是 ELF/musl aarch64，取 Linux 分支语义正确；`-fcf-protection` 由 `$(ARCH)` 的 x86 条件挡住，`-latomic` 由 `$(findstring gcc,$(CC))` 条件挡住（本机 `-latomic` 实测不可用：`ld.lld: error: unable to find library -latomic`）。
4. **`LIBS` 重建**：Makefile 第 326 行链接顺序是 `$(LIBS) $(LDFLAGS)`，而 `LIBS = -lm -lopusfile -lglib-2.0 -lpthread $(PKG_LDFLAGS)` ⇒ 若不改写，`-lopusfile/-lglib-2.0` 会出现在第一个 `-L` 之前而找不到库。改法是把 `pkg-config --libs` 的结果置于 LIBS 头部，再把上游字面量接在后面（`-lstdc++` 保留：OHOS 工具链实测可链接，`clang++ -lstdc++` rc=0）。`pkg-config` 的取值用 shell 命令替换在 `export PKG_CONFIG_PATH=<generators_folder>` 之后完成——简单命令上的变量赋值对该命令自身词内的命令替换不可见，所以必须 `export`。该姿势对应 **E468**（`PkgConfigDeps` 只写 `.pc`、不扩 `PKG_CONFIG_PATH`），与「为什么不用 E468 的处方写法」一并见第 8 节。
5. **opusfile 头文件目录**：`opusfile/0.12` 把 `opusfile.h` 装到 `<pkg>/include/opus/`，但它的 `package_info()` 没有导出这一层，Conan 的 `PkgConfigDeps` 于是只给 `-I<pkg>/include`，裸 `#include <opusfile.h>` 编不过（第一条真实错误：`src/sound/webm.h:21:10: fatal error: 'opusfile.h' file not found`）。配方自带该包**自己的** `lib/pkgconfig/opusfile.pc` 写的正是 `Cflags: -I${includedir}/opus` ⇒ 本配方按上游元数据把该目录补进 `PKG_CFLAGS`，**不去改 opusfile 的配方**（那是另一个 PR）。**实测补证（W4 r1 K6，此前属推断）**：`grep -n includedirs archives/o/opusfile/0.12/conanfile.py` = **0 命中**，其 `package_info()`（第 246-259 行）只设 `components` 的 `libs`/`requires`/`cmake_target_name`/`pkg_config_name`，不设任何头目录 ⇒ Conan 侧只给默认 `<pkg>/include`，`<pkg>/include/opus` 确实不在搜索路径里；第一条真实错误 `src/sound/webm.h:21:10: fatal error: 'opusfile.h' file not found` 与之同向。
6. **gettext 符号族**：`libglib-2.0.so` 的未定义符号是 `g_libintl_gettext`/`g_libintl_bindtextdomain`/`g_libintl_textdomain`，其 `NEEDED` 已列 `libintl.so.8`。`archives/a/abr2gbr/1.0.2` 的 `-L/lib -l:ld-musl-aarch64.so.1` 处方**在本机不适用**（实测 `nm -D /lib/ld-musl-aarch64.so.1 | grep -c g_libintl` = 0），所以改为直接 `requires("proxy-libintl/0.5", run=True)` 并把 `intl` 加入 pkg-config 模块表。
7. **`USE_FAAD=0`**：绕开 Makefile 第 209/215 行烧死的 `/opt/homebrew`、`/usr/local/lib -lfaad` 探测（本仓 OHOS 侧不可假设 `/usr/local` 可写，且 faad2 未适配）。
8. **`make install` 用 `PREFIX=<package_folder>` 且 build/install 两次传同一套变量**：`install: all` 会复用已编译对象，不重编；`PREFIX_RAW`/`KEW_DATADIR_RAW`/`LOCALEDIR_RAW` 因此与安装布局一致（`bin/kew`、`share/man/man1/kew.1`、`share/kew/themes`、`share/kew/layouts`、`share/locale/{zh_CN,ja}/LC_MESSAGES/kew.mo`、`share/applications/kew.desktop`、`share/icons/hicolor/512x512/apps/kew.png`）。R20 的 DESTDIR 口径已废弃，故不使用 DESTDIR。`STRIP=0`（本机 MAC 拒绝对 strip 后的二进制 `exec`，同 `archives/a/abduco/0.6` 的处置）。
9. **上游缺陷补丁 `patches/0001-fix-lyrics-source-suffix.patch`**：Makefile 第 242 行 `SRCS` 写的是 `src/loader/lyrics.c`，而 tag `v4.2.5` 的 tarball 里只有 `src/loader/lyrics.cpp`（`ls src/loader/` 实测：`lyrics.cpp`、`lyrics.h`、`song_loader.*`、`tagLibWrapper.*`）⇒ 原样构建停在 `No rule to make target`。补丁把该条目改成 `.cpp`，并把 `OBJS_C` 用 `$(filter %.o,...)` 收口、新增 `OBJS_CPP`（同样用 `$(filter %.o,...)`）并入 `OBJS`；Makefile 第 302 行本就存在 `$(OBJDIR)/%.o: src/%.cpp` 规则，因此 `lyrics.cpp` 由 C++ 规则编译并链接。补丁本地 `patch -p1 --dry-run` 与正式应用均通过；`conan create` 日志第 152 行确认 `Apply patch (portability)`。
10. **消费者测试的运行环境交接**：`env="conanrun"` 会把 `LD_LIBRARY_PATH` 指到 proxy-libintl 的 `<pkg>/lib`，而 `libintl.so.8` 只导出 `g_libintl_*` 一族；DT_RUNPATH 的优先级低于 `LD_LIBRARY_PATH`，于是测试解释器自身先炸（实拍 `Error relocating .../libpython3.14.so.1.0: libintl_gettext: symbol not found`）。改法是测试入口脚本先取 `${LD_LIBRARY_PATH:-}` 再 `unset`，把该串经 argv 交给用例，只对**被测二进制**生效。

## 编译结束

（两档以上 RREV 的逐字取值、复算方式与出处见本文末「收口核账」第 2 节；该节由收口-kew 于收口轮实测填写。）

**最终状态**: built
---

**编译结束**: 2026-09-27 06:59
**最终状态**: built

## 收口核账（代号 收口-kew，2026-09-27 收口轮，全部本轮实测复算）

### 1 交付态取源：已按 R39 / PF7 还原为官方址

提交态 archives/k/kew/4.2.5/conandata.yml 第 2–3 行原文：

- url: "https://github.com/ravachol/kew/archive/refs/tags/v4.2.5.tar.gz"
- sha256: "a17f4acd54c78511bb14fc4e02aaaafc351f640388c3d29254f4397edfdc16a1"

官方址哈希本轮**自算 3 次采样**（B 机 curl -sSL 直连，三次均 http=200、size_download=12573259 B，落盘 ~/tmp/uc2/z74-kew/samples/off-1..3.tar.gz）：三枚 sha256 全部为 a17f4acd54c78511bb14fc4e02aaaafc351f640388c3d29254f4397edfdc16a1，与配方声明逐字相同；本机绿跑预取件 .build-cache/predl_cache/ba921ade_v4.2.5.tar.gz 的 sha256sum 实测亦为同值 ⇒ 绿跑构建所用字节 = 官方址字节，非镜像另制品。

- 前棒「B 机对 codeload.github.com 不可达、必须挂 ghfast 镜像」的结论**本轮未复现**：三次直连全部 200 到底。该结论按瞬时网络抖动处理，不作为镜像址的理由。
- 还原姿势：先留备份 conandata.yml.orig（ghfast 态原文），再逐字替换 url 行；未就地猜内容、未改动 sha256 字段。
- 为什么必须还原：SKILL.md R39（源码 URL 必须官方源）+ §Step preflight 的 **PF7 源URL闸**把 ghfast.top 等 14 个镜像域名、file:// 泄漏与绝对路径一律列为拦截项 ⇒ 上一枚提交 96f87e7e8f 的提交态在 CI 侧属必红项，本笔收口提交即修此项。

### 2 ★三档 RREV（url 属配方内容，绝不当同一修订引用）

| 档位 | RREV | 该档 conandata 的 url 内容 | 取值出处 |
|---|---|---|---|
| 交付态 | e94dcf0c7cbd9904b18225e8654a39fe | 官方 GitHub tag 址 | 本轮 conan export（2026-09-26 23:13:50 UTC；带 --user=ohpcd --channel=stable 再导一次同值，见下） |
| 绿跑当时 | fd6577ad750512d5ce4d17d2aac44345 | file:// 本机预取件 | reports/w3-local-ci.log:122（Pre-download 段 line 107–111 先把 conandata 改写为 file:// ，随后才导出）；引用见同日志 :201/:405/:444 |
| 镜像态（上一枚提交态） | d63e88f879dddcd24ad15b9e9618c335 | ghfast.top 前缀址 | reports/conan-create.log:10（2026-09-26 23:00:03 UTC） |

- 复算方式（不采信记忆值）：把整个 4.2.5 目录复制到 ~/tmp/uc2/z74-kew/rrevlab/lab，只换 url 行再 conan export。三档结果与日志逐字命中，其中镜像态连缓存目录名 p/kew1e1159d5ae7e0 都与 conan-create.log:9 一致 ⇒ 归因可靠。
- user/channel 不进配方修订：交付态分别以 kew/4.2.5 与 kew/4.2.5@ohpcd/stable 导出，rrev 同为 e94dcf0c…。
- 三档共用同一枚 PKGID：9762204022b00a038daf4deca7c0ad22a7f21b5b（reports/conan-create.log:88、reports/w3-local-ci.log:201）。
- **对 CI 的如实预期（不粉饰）**：CI 与本地同走 build_and_test.sh 的 Pre-download 段，导出那一刻 conandata 已是指向 CI 机器绝对路径的 file:// ⇒ CI 侧 rrev 既不等于交付态 e94dcf0c，也不保证等于本地绿跑的 fd6577ad（fd6577ad 内嵌 B 机 worktree 的绝对路径）。因此本包**不宣称「CI 会首次真跑官方址」**，只宣称：提交态 URL 为官方址且哈希三样自算一致，绿跑证据建立在字节相同的同一份 tarball 上。

### 3 W3 证据自洽核对（复算，非照抄）

reports/w3-local-ci.log 与同目录 .ci-result.json 三字段对账：

- exit_code: 0，step: W3_local_ci，timestamp: 2026-09-27T07:04:23.791662。
- log_sha256 声明 ddd6887a148dd9abc4a050b5c521b8dfb6be9ac5e4195cd22ed2fa295bd0178f；本轮 sha256sum reports/w3-local-ci.log 实算 **同值**。
- integrity_hash 声明 a2e9011212f9ae41；本轮按 sha256("2026-09-27T07:04:23.791662:kew:4.2.5:0") 取前 16 位复算 = **a2e9011212f9ae41**（口径同 scripts/ohc/finish.py 的收尾签名式）。
  ⇒ 该文件由 harness 生成、未手写、未被事后篡改；绿证据与日志绑定成立。

### 4 conan-verify 报告的逐节子行读数（表头 PASS 不等于该节真判过）

按「## Gx: 判决行 + 紧邻子行」口径实读 reports/conan-verify-report.md（Verdict: PASS，Date 2026-09-27T07:00:09）：

- G0 表头 PASS，子行为 Knowledge hit: E490 且带「⚠️ 已知风险 E490 未在配方中处理」。E490 讲的是 autotools 辅助脚本可执行位；kew 是裸 Makefile，本轮解包交付 tarball 复核：无 configure / config.guess / config.sub / install-sh，Makefile 仅 3 枚 .PHONY ⇒ **该 hit 属误配，不构成本包待办**，但也不写作「已处理」。
- G1 表头 PASS，子行逐条 ✅（name/version/source/build/package/package_info/export_sources/补丁调用/conandata 完整/test_package 与 MANIFEST 存在），R26 为 ℹ️ 无静态配置。
- G2 表头 PASS，子行 ✅ conan create 成功，日志 archives/k/kew/4.2.5/reports/conan-create.log。
- G3 表头 PASS，子行是 ℹ️「无 lib/ 目录（纯可执行包）」+ ✅ 无系统同名库冲突 ⇒ 信息行，不含库内容判决。
- G4 表头 PASS，子行「⚠️ 无法找到程序包 ID」⇒ **skip，不计入 PASS**。
- L2 / L4 / L5 三节表头均 PASS，子行一律「⏭️ 跳过（无 cache 路径）」（原文：`reports/conan-verify-report.md:42-43`、`:45-46`、`:48-49`）⇒ **这份 skip 只属于 conan-verify 档**。
- ⚠ 它 **不等于 W3 档没跑**：同一批 L2/L4/L5 在 W3 本地 CI 里是真执行过的，判决是 L4=pass、L5=pass、**L2=skip**，见下一节 4b。两档不得互相代表，也不得合并成「未执行」。
  ⇒ **conan-verify 档**的真实有效判决只落在 **G1 + G2（外加 G3 的无冲突项）**；该档的 G4 与 L2/L4/L5 四节未执行，任何汇报不得写成「全节 PASS」。

### 4b W3 本地 CI 档的 L2/L4/L5 真实判决（含 L2 负信号；W4 r1 K2 补披露）

`reports/w3-local-ci.log` 原始行（`nl -ba` 定位，逐字照抄）：

- `525: [step] L4: Scanning patches for dangerous functions...`
- `526: [step] L5: Baseline artifact check...`
- `527: [ok] L5: bin/ has content`
- `531: [step] L2: Smoke test (version/help check)...`
- `532: [warn] L2: kew --version/--help failed (non-blocking)`
- `536: L2_RESULT=skip: kew version/help failed`
- `537: L4_RESULT=pass: patches clean`
- `538: L5_RESULT=pass: bin/ has content`

同档的 `ci-metadata.json` 逐字一致：第 18 行 `"L2": {"result": "skip", "detail": "kew version/help failed"}`、第 19 行 L4 = pass（patches clean）、第 20 行 L5 = pass（bin/ has content）。

⇒ 真实判决是 **L4=pass、L5=pass、L2=skip**，**不是「未执行」**；而 L2 这条负信号此前任何载体都没披露过，本节即补披露。

- **L2 为什么 skip（根因，与配方无关）**：harness 的 L2 步骤在 `ci/conan/build_and_test.sh:1676-1697`，形如 `timeout 15 "$bin_file" --version </dev/null >/dev/null 2>&1` 再 `elif timeout 15 "$bin_file" --help ...`——**裸跑，不注入 conan run env**（既不走 `env="conanrun"`，也不给 `LD_LIBRARY_PATH`）⇒ musl loader 取不到 DT_NEEDED 里的 `libglib-2.0`/`libchafa`/… 等依赖 ⇒ 两个参数都非零，harness 按 non-blocking 记 skip。这与适配点 10 是同一机理的正反两面：是 run env 决定这对参数能不能跑，**不是 kew 本身不能跑**。
- **与消费者测试不矛盾**：`test_package/test_kew.py:207-224` 走 argv 注入 run env 后，`kew --version exits 0`、`kew --help exits 0` 两条断言在 36 条里全 PASS（`SUMMARY kew consumer: total=36 passed=36 failed=0`，`reports/conan-create.log:222`、`reports/w3-local-ci.log:518`）。
- **CI 侧同源**：CI 跑的是同一个 `build_and_test.sh`，也会打印 `L2_RESULT=skip: kew version/help failed`。PR 正文/notes 若不披露就是与 CI 打架。
- 固定口径：**G4 与 L2/L4/L5 的「无 cache 路径」skip 属 conan-verify 档；W3 档 L4/L5 = pass、L2 = skip（裸跑取不到 DT_NEEDED）**。

### 5 测试口径同源（静态站点数与展开算式）

- 消费者断言算式（可复核）：test_package/test_kew.py 内 rec.check 调用站点 **25 处**（grep -c 计数）；第 135/137 行是同一条 ELF magic 判据的 if/else 两分支、运行时只执行一枚 ⇒ **-1**；第 155 行位于 for prefix in (...) 循环内，前缀元组实点 **13 枚**（libglib-2.0、libgio-2.0、libgobject-2.0、libgmodule-2.0、libchafa、libfftw3f、libopus、libopusfile、libvorbis、libvorbisfile、libogg、libintl、libc++）⇒ 净 **+12**。
  **25 - 1 + 12 = 36 = 声明数**（声明 36 ≤ 实测 36，无放宽判据、无跳过断言、无只数标题不算断言的凑数）。
- 实测汇总行两处逐字相同：reports/conan-create.log:222 与 reports/w3-local-ci.log:518 均为 SUMMARY kew consumer: total=36 passed=36 failed=0；w3 日志内 PASS 行实点 36、FAIL 行 0。
- 四处同源核对表（断言数）：notes.md（本表，36）/ test_package/MANIFEST.yml（assertion_count: 36）/ 版本级 manifest.yaml（test_results total 36、passed 36、failed 0、skipped 0）/ 软件级 manifest.yaml + README.md（36）/ reports 两份日志的 SUMMARY 行（total=36 passed=36 failed=0）⇒ **同值**。
- 四处同源核对表（W4 r1 起新增两列）：**上游分母** notes.md（0）/ test_package/MANIFEST.yml（denominator 0、find_matches_non_test 2）/ 版本级 manifest.yaml（`upstream_tests.denominator: 0`）/ 软件级两枚（0）⇒ **同值**；**门禁判决** notes.md 第 4 节（conan-verify 档 G4/L2/L4/L5 = skip）+ 第 4b 节（W3 档 L4/L5 = pass、L2 = skip）/ 版本级 manifest.yaml 的 `local_ci` 块 / `ci-metadata.json` 与 `reports/w3-local-ci.log:531-538` 原始行 ⇒ **同值、分档不混写**。
- 上游测试独立清点（收口-kew 本轮自跑，未复用前棒输出；解包交付 tarball 到 ~/tmp/uc2/z74-kew/census 后执行）：
  1) grep -nE "TESTS|add_test|^check:|^test:|\.PHONY" Makefile ⇒ 只命中 .PHONY: install / uninstall / clean 三行，无 TESTS、无 add_test、无 check 或 test 目标；
  2) test -d t、test -d tests、test -d test ⇒ 三者皆不存在；
  3) find . -iname "*test*" ⇒ 仅 pages/testimonials.html 与 website/site_src/testimonials.md 两枚文档页。
  ⇒ **分母 0、可用 0、上游测试数 0**；find 命中的 2 枚均为文档页，另记为 `find_matches_non_test: 2`，**不计入分母**。判据（本轮补写，此前只在 detail 里隐含）：分母 = 可注册/可执行的上游用例数 = `tests/` 目录数 + Makefile `check`/`test` 目标数 + `ctest`/`add_test` 注册数。口径与 `test_package/MANIFEST.yml` 的 `upstream_test_census`（denominator 0 / usable 0 / tests_directories 0 / test_named_files 0 / registered_tests 0 / make_check_target false / make_test_target false / find_matches_non_test 2）同值；「上游无成体系测试」的依据就是上面 1)–3) 三条命令，未放宽判据。⇒ PR 正文的上游口径据此写「上游 0」，**不得写「上游 2」**（R51/rule4 少报口径）。
- R38/L0k：本包产出可执行文件，软件级 archives/k/kew/commands.json 已声明（type tool、versions 4.2.5 的 ref kew/4.2.5、binary true）。

### 6 收口边界与未做完事项（如实）

- 本窗按指令**未碰平台、未碰任务登记表**：$P note/stage/run/issue/create-pr/presubmit/block 一律未调用；未建 PR、未触发 CI、未 request-review。
- 未做（技术项）：①交付态（官方址）从未在 CI 上真跑过，本窗只有本地 W3 绿证据，且绿证据绑的是 file:// 档 rrev；②**conan-verify 档**的 G4/L2/L4/L5 四节子行（无 cache 路径）本地补不了，要等 CI 侧判决。**W3 档的 L2/L4/L5 不在此列**——那三节本地是真执行过的（L4=pass、L5=pass、L2=skip），判决见第 4b 节，不再写成「本地补不了」；③result.json 未随本笔收口提交重生成（四件套第 ④ 项，属持 PR 号窗口的义务）；④本包未做 conan create 复跑（预算纪律：重建成本高，优先用盘上绿证据 + 只算 rrev）。
- 播放主流程在本机结构性不可行的结论未变（无 libasound、/dev/snd Permission denied），维持「不声称能出声」口径。

### 7 PF7 源 URL 闸直证（本轮调 scripts/ohc/preflight.py 的 _pf7_classify 实跑）

- 交付态官方址 https://github.com/ravachol/kew/archive/refs/tags/v4.2.5.tar.gz → 返回 None（**无违规**）。
- 上一枚提交 96f87e7e8f 的 ghfast.top 前缀址 → 「镜像前缀 ghfast.top（CI 自动加镜像回退，手写即 R39 违规 579 例）」= **必红项**。
- file:// 形态 → 「file:// 本机缓存泄漏（CI 预下载改写未还原，71 例）」= 必红项（故提交态绝不可留 file://）。
  ⇒ 本笔收口提交修掉的正是这一项；.ci-result.json 的签名式亦已按 scripts/ohc/finish.py:252 复算命中（见第 3 节）。

### 8 E 编号命中清单（W4 r1 K3 补申报：此前正文只提到 E392 与 E490）

| E 编号 | 条目主旨（`knowledge/doc/*.md` 实读标题） | 本包命中处 | 落地方式 |
|---|---|---|---|
| E392 | Raw makefile Conan 配方的三个通用陷阱：BadZipFile 编码器误选 / compiler_executables 字典获取 / make 默认 cwd 错误 | 适配点 1 | `get(..., filename="kew-4.2.5.tar.gz")`；`conf.get(..., check_type=dict)` 后 `.get("c")/.get("cpp")`；`make cwd=self.source_folder` |
| E468 | PkgConfigDeps writes .pc files but does not extend PKG_CONFIG_PATH, so upstream PKG_CHECK_MODULES probes miss Conan metadata | `conanfile.py:215` 把 generators 目录放进 `PKG_CONFIG_PATH` | 见下方「为什么不用 E468 的处方写法」 |
| E525 | OHOS 下 make 应统一 -j1 | `conanfile.py:215` 的 `make -j1`（build 与 package/install 两次同调） | 与条目处方一致 |
| E524 | configure 反复报 C compiler cannot create executables / 依赖缺失：检查共享 SYS_PREFIX 注入污染与逐项 REQUIRED 依赖 | Makefile 第 209/215 行的 `/opt/homebrew`、`/usr/local/lib -lfaad` 硬编码探测 | `USE_FAAD=0` + `PREFIX=<package_folder>`（适配点 7、8） |
| E142 | link-libintl_glib | `libglib-2.0.so` 的未定义符号是 `g_libintl_*`（适配点 6） | `requires("proxy-libintl/0.5", run=True)`，`intl` 进 pkg-config 模块表 |
| E508 | intl-wrapper | `proxy-libintl` 即该包装侧制品；`libintl.so.8` 已在 `libglib-2.0.so` 的 NEEDED 里 | 同上；run env 抢占机理见适配点 10 |

- 取证命令（本轮自跑）：`grep -h "^# E" knowledge/doc/E468.md knowledge/doc/E525.md knowledge/doc/E524.md knowledge/doc/E142.md knowledge/doc/E508.md knowledge/doc/E392.md`。
- **为什么不用 E468 的处方写法（`self.buildenv_info.append_path('PKG_CONFIG_PATH', self.generators_folder)`）而是自行导出该变量**：
  ① `buildenv_info` 只有被 `VirtualBuildEnv` 生成器消费才会落进 `conanbuild` env，而本配方 `generate()`（`conanfile.py:158-159`）只跑 `PkgConfigDeps(self).generate()`，**没有 `VirtualBuildEnv`** ⇒ 照抄该处方不落地；
  ② 本包要在**同一条 make 命令**里做两次 `$(pkg-config --cflags/--libs ...)` 命令替换（`conanfile.py:217-219`），而「简单命令自带变量赋值」对该命令自身词内的命令替换不可见，所以必须导出；
  ③ 改用 `--with-pkg-config` 之类会改写 conan 注入的工具签名，风险大于收益。
  `_make_cmd` 由 `build()` 与 `package()` 以同一套变量各调一次，导出只活在该次 `self.run(env="conanbuild")` 的子 shell 里，**不污染配方进程的共享状态**。审计 K3 明确「不判功能错」，本笔只补申报，⛔ 未改 `conanfile.py`（改动会翻 rrev、作废已绑定的 W3 证据锚）。
