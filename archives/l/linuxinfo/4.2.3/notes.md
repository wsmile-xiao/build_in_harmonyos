# linuxinfo 4.2.3 适配笔记

## 编译环境
- 构建系统: autotools（automake 1.16 / autoconf 2.72 生成的 `configure`，无 `config.h`，全靠 `DEFS` 注入宏）
- 编译日期: 2026-09-27（主理-73 棒在 A 机真机执行 conan create / conan-verify / finish-W3）
- 编译器: clang 15（`aarch64-unknown-linux-ohos`）
- 状态: **built —— W3 本地 CI 全绿（2026-09-27，L1 19/19；读数与证据见文末「9. 主理-73 收尾记录」）**

---

## 0. 本包到底是什么（决定测试口径）

上游是维护者 Helge Kreutzmann 自己的一个极简单二进制命令行工具：

```
$ linuxinfo
HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026
Three ARM v7 instruction set 528MHz processors, 2001.00 total bogomips, 29xxxM RAM
System library 2.38
```

三段式输出，来源各不相同（`linuxinfo.c: main()`）：

| 输出行 | 数据来源 | 代码位置 |
|---|---|---|
| 第 1 行 | `uname(2)` 的 `sysname/nodename/release/version` | `linuxinfo_common.c: GetOperatingSystemInfo()` |
| 第 2 行 | `/proc/cpuinfo`（按 arch 分派到 `linuxinfo_arm.c`）+ `/proc/meminfo` | `GetHardwareInfo()` + `getphysicalmemory()` |
| 第 3 行 | **glibc 专有符号**探测 libc 版本 | `GetSystemLibcInfo()` ← 本次崩溃点 |

命令行面（`main()` 逐字读源码确认，不是猜的）：
- `-v` → `printf("%s %s\n", argv[0], VERSION)`，返回 0。`VERSION` 由 `DEFS` 注入为 `"4.2.3"`。
- `-h` → 版本号 + 两行用法，返回 0。
- **其余任意实参被当作 cpuinfo 文件路径打开**（`cpuinfo_fd = open(argv[1], O_RDONLY)`）
  → 这是本包最实用的可测面：可以喂构造的 cpuinfo 得到**逐字可预期**的输出。
- 打开失败 → stderr 打印 `Unsupported option or file %s not found.`，`return -1`（shell 侧 255）。
- 无实参时打开 `/proc/cpuinfo` 失败 → `return -2`（254）。

---

## 1. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸跑 `./configure` 直接失败：`configure: error: cannot guess build type; you must specify one` | 上游 `config.guess`（快照 `2024-07-27`）不认识 HarmonyOS 上 `uname -s` 返回的 `HarmonyOS`。一手实测：`sh config.guess` 打印 `UNAME_SYSTEM = "HarmonyOS"` 后落入 unknown 分支 | **不补 config.guess/sub**。同包的 `config.sub`（`2024-05-27`）**已经**认 `ohos` 后缀：实测 `sh config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`、rc=0。所以显式喂 `--build/--host` 三元组即可（R21：平台检测优先于改生成文件） |
| 2 | 三元组给全之后仍失败：`./config.status[768]: can't create ./confMeoCnp/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | **E011/E114/E118 家族**。`config.status` 硬编码 `{ tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`; ...}`。HMDFS 的 UID 映射（目录属主 UID 20001006 ≠ 进程实际 UID）+ 继承来的 setgid 位，把 0700 目录落成 `drwx--S---`，**连属主都不能在里面创建文件** | `patches/0001-configure-umask.patch`：4 处 `umask 077` → `umask 022`（`configure` 第 8743/8748/10185/10190 行，两个 `CONFIG_FILES` 段落各一份）。属既有机制，不新增知识 |
| 3 | 上游 `Build-Depends` 里的 `po4a` 与 `libpcre2-dev` 要不要变成 `requires()`？ | 都不必需：`m4/pcre.m4` 的 `AC_ARG_WITH(pcre,...)` 缺省分支是 `with_pcre=no`，实测 `configure` 输出 `checking for --with-pcre... no` 且 `Makefile` 里 `PCRE_LINK = ` 为空；正则分支只在 x86 的 `regstrcmp()` 用到，aarch64 走 `linuxinfo_arm.c` 的 `CPU implementer` 静态查表。`po4a` 只生成多语言 man，官方件已自带成品 `po4a/linuxinfo.1`，`LINUXINFO_PROG_PO4A` 找不到 po4a 时 `USE_PO4A=no`，实测 `po4a/Makefile` 退化成空目标 `all-local-no:` | **`requirements()` 留空**（不是"未发布所以 block"，是根本不需要）。再加 `--disable-nls` 把 `USE_NLS=no`/`LIBINTL=` 钉成确定形态，`po/` 不再需要 `msgfmt`。交叉印证：Debian 自己也把 `libpcre2-dev` 限死成 `[i386] [amd64] [x32]`，arm64 不拉 |
| 4 | （预判并已在补丁内解决）真机运行会 SIGSEGV | `GetSystemLibcInfo()` 对 `gnu_get_libc_version`/`__libc_version`/`__linux_C_lib_version` 三个 `.weak` 符号做**无空指针保护**的三选一，末支直接 `ptr = __linux_C_lib_version` 后 `while (!isdigit(*ptr)) ptr++;`。OHOS 是 musl，实测 `nm -D /lib/ld-musl-aarch64.so.1` 共 1954 个动态符号、这三个符号 **0 命中**（同法在 `printf` 上命中 1，证明探测法有效）→ 三个弱符号地址都归 0 → 读地址 0 | `patches/0002-linuxinfo_common-libc-version-probe.patch`：把末支改成 `else if (&__linux_C_lib_version != 0)` + `else ptr = NULL`，并在 `while` 前加 `if (ptr == NULL \|\| *ptr == '\0') return;`，落回该函数**本来就写好**的 `"Unknown"` 默认值。**不含任何平台宏**（PF5 安全），对 glibc 系统行为零改变 |

### 已试失败的方案（不要重复踩）

1. **只改外层 `umask`（不改 configure）**：`( umask 022; ../configure ... )` 照样死在 `subs1.awk`。
   原因：`umask 077` 是硬编码在 `config.status` 内部的子 shell 里，外层 umask 传不进去。实测 rc=1。
2. **`--disable-nls` 想绕过问题 2**：不行。`--disable-nls` 只影响 `USE_NLS`/po 目录，
   `config.status` 的临时目录逻辑在它之前/之后都会跑，同样 rc=1。二者**互不替代**。
3. **把 po4a 声明成 required**：错。它是文档生成工具，官方件里 man 页已是成品。
   真把它列进 `requires()` 反而会牵出一个无意义的构建依赖。
4. **用 `conan list` 通配判断 pcre2 可用不可用**：方法本身就违规（R35）。本次改成读
   `m4/pcre.m4` 的缺省分支 + `configure` 实测输出 + 生成的 `Makefile` 里 `PCRE_LINK` 为空，
   三处一手证据直接得出"不需要 pcre2"，比查仓更彻底。

---

## 2. 最小复现（接力棒/复核者可逐字重跑）

```bash
# 前置：export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
D=$HOME/tmp/uc2/z68-linuxinfo; mkdir -p $D && cd $D
curl -sS -o official.tar.xz -w "%{http_code} %{size_download}\n" \
  https://www.helgefjell.de/data/linuxinfo/linuxinfo-4.2.3.tar.xz
sha256sum official.tar.xz     # 期望 003123eebb097fd8e12a299bd4ea8b9ed6988311b2412df132b148f3ca9a705a

rm -rf repro && mkdir repro && tar -xf official.tar.xz -C repro && cd repro/linuxinfo-4.2.3
mkdir b && cd b

# (A) 问题 1 —— 不给三元组
../configure --prefix=/tmp/p ; echo rc=$?    # rc=1  cannot guess build type; you must specify one

# (B) 问题 2 —— 给了三元组，仍死在 config.status
../configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos --prefix=/tmp/p ; echo rc=$?
#   ./config.status[768]: can't create ./confXXXXXX/subs1.awk: Permission denied
#   config.status: error: could not setup config files machinery

# (C) 两枚补丁都打上 → 通过
patch -p1 -d .. -i <本包>/patches/0001-configure-umask.patch
patch -p1 -d .. -i <本包>/patches/0002-linuxinfo_common-libc-version-probe.patch
../configure --disable-nls --build=aarch64-linux-ohos --host=aarch64-linux-ohos --prefix=/tmp/p ; echo rc=$?
#   实测 rc=0，生成 Makefile / po/Makefile.in / po4a/Makefile
grep -E '^(USE_NLS|USE_PO4A|LIBINTL|LTLIBINTL|PCRE_LINK|VERSION) =' Makefile
#   USE_NLS = no / USE_PO4A = no / LIBINTL = / LTLIBINTL = / PCRE_LINK = / VERSION = 4.2.3
```

> ⚠ `/tmp` 在设备上是只读 erofs（`/dev/block/dm-0 /tmp erofs ro,...`），上面 `--prefix=/tmp/p`
> 只是让 configure 尽早失败用的占位；真跑构建要把 prefix 指到可写目录。

---

## 3. 测试统计（设计口径；真实数字待接力棒 W3 回填）

### 表 A — 上游 vs 适配后用例数

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游单元测试 | 0 | 一致 | 上游无任何自动化测试，清点证据见 `test_package/MANIFEST.yml`（`find -iname 'test*'`=0、`Makefile.am` 无 `TESTS`/`check` 目标） |
| 消费者测试（test_package） | 14 | +14 | TC-00～TC-04：可执行定位 / `-v` / `-h` / canned cpuinfo 逐字断言 / 错误路径 |
| 鸿蒙特有测试 | 5 | +5 | TC-05.1～05.5：真机无参读 `/proc/cpuinfo`+`/proc/meminfo`、`uname` sysname 断言、**patches/0002 的 SIGSEGV 回归位** |
| **合计** | **19** | **+19** | |

### 表 B — 执行结果（2026-09-27 主理-73 棒实测回填；来源 reports/w3-local-ci.log 的 TC 段）

| 测试类型 | PASS | FAIL | SKIP | 合计 |
|----------|------|------|------|------|
| 消费者测试（test_package） | 14 | 0 | 0 | 14 |
| 鸿蒙特有测试 | 5 | 0 | 0 | 5 |
| **合计** | **19** | **0** | **0** | **19** |

> 2026-09-27 主理-73 回填：`conan create` 真跑 test_package 实测 `PASS=19 FAIL=0`
> （w3-local-ci.log 内 `[PASS]` 恰 19 条、无 `[FAIL]`；三列相加=19，分母未动）。

---

## 4. 适用边界与已知局限

- **只在 AArch64/armv8 上验证过**（`linuxinfo_arm.c` 分支）。`conanfile.validate()` 对其它 arch
  直接抛 `ConanInvalidConfiguration`。上游另有 15 个 arch 分支，其中 x86 那条会额外牵出
  `--with-pcre` → 真要做 x86 得重走 W0。
- 本包**读的是 Linux 风格 `/proc`**。鸿蒙 PC 上 `/proc/cpuinfo`、`/proc/meminfo` 实测可读
  （`/proc/cpuinfo` 有 `Processor/BogoMIPS/CPU implementer/CPU architecture` 等键），
  所以功能面成立；但这属于"依赖鸿蒙内核保留 Linux `/proc` 兼容"，内核侧改动会让它失效。
- `--disable-nls` ⇒ 输出恒为英文（`ordinals` 走 `__()` 直通），不装 `.gmo`。
  若后续要中文输出，需另外引入 gettext 运行时并去掉该开关，属新工作。
- man 页只装英文 `po4a/linuxinfo.1`（官方件自带），不生成 9 种翻译版。

### 待验证（接力棒留意，撞上才升 B）

1. `linuxinfo_arm.c` 的 `implementer[]` 表**没有 `"0x48"`（HiSilicon/麒麟）**，本机
   `/proc/cpuinfo` 恰是 `CPU implementer : 0x48` ⇒ 预期输出 `Unknown ...`。
   另外 `processors` 靠 `Type`/`Processor`/`CPU implementer` 行计数，ARM64 只有
   `processor`（小写）不计数 ⇒ 真机可能报 `Unknown ... processors`。
   **这是上游数据表陈旧，不是 HarmonyOS 移植缺陷** ⇒ 默认不改（改了就偏离上游版本）；
   若接力棒认为要给上游提补丁，先按 §9 报用户，别顺手打进本 PR。
2. 本包 `po/Makefile.in` 在 `USE_NLS=no` 下是否真的零动作，尚未跑 `make` 验证（起草棒不做构建）。
   若 `make` 仍去调 `msgfmt`，优先怀疑 `--disable-nls` 没生效，而不是急着 `tool_requires gettext`。

---

## 5. 官方货源定性与采样矩阵（本包最容易做错的地方）

SCT 台账给的是 **Debian 池址**，那是下游重打包位，按 PF7 黑名单**绝不能**当配方货源，
只拿来交叉核验哈希。真正的官方货源是从**包内 README 自述**顺出去的：

> `README`: "The latest releases are always available at:
> `http://www.helgefjell.de/linuxinfoitem.php?name=download`"
> 且注明旧址 `http://www.munted.org.uk/programming/` "no longer active"。

抓该下载页（http/https 两种形态各 3 次均 200 / 4701–4700 B）后，页面正文逐条列出
`http://www.helgefjell.de/data/linuxinfo/linuxinfo-<ver>.tar.xz` 与配套 `.sig`，
版本覆盖 1.9.2 → 4.2.3 全链，**4.2.3 在列**。维护者邮箱 `debian@helgefjell.de`
与包内 `AUTHORS`/`ChangeLog`/`.dsc` 的 Maintainer 一致，Debian 的 `Homepage` 字段
也指向同一域名 ⇒ `www.helgefjell.de/data/linuxinfo/` 就是官方发布目录。

### 采样矩阵（每址 GET 全量 ≥3 次，`curl -I` 不计入）

| 候选址 | 3 次 HTTP | 3 次字节 | magic | sha256 前 8 位 |
|---|---|---|---|---|
| `https://www.helgefjell.de/data/linuxinfo/linuxinfo-4.2.3.tar.xz` | 200 / 200 / 200 | 169860 ×3 | `xz compressed data` | `003123ee` |
| `http://www.helgefjell.de/data/linuxinfo/linuxinfo-4.2.3.tar.xz` | 200 / 200 / 200 | 169860 ×3 | `xz compressed data` | `003123ee` |
| `.../linuxinfo-4.2.3.tar.xz.sig`（detached 签名） | 200 / 200 / 200 | 236 ×3 | `ASCII text` | — |
| `http://www.helgefjell.de/data/linuxinfo/`（目录索引） | 403 ×3 | 239 | HTML | — 目录不可列，但**对象可取**，不影响货源成立 |

https 三次耗时 16.8s / 17.0s / 7.4s —— 站点慢但三次零失败，取 https 形态入 conandata。

### 交叉核验（只核哈希，不作货源）

`deb.debian.org/pool/main/l/linuxinfo/linuxinfo_4.2.3.orig.tar.xz`
→ 200 / 169860 B / xz / sha256 `003123eebb097fd8e12a299bd4ea8b9ed6988311b2412df132b148f3ca9a705a`，
与 `.dsc` 的 `Checksums-Sha256`、`Files`(md5 `1233bd580fd6982bf77a88646dce8001`) 一致，
也与上面官方址三次同值。

> ⚠ 同值只证明"官方件 == Debian `.orig` 件"（同一个文件），**不证明"完整可编"**。
> 后者由 §2 的一手 `./configure` 实测（打完两枚补丁后 rc=0、`Makefile` 关键变量齐）单独支撑。

### 排除项

- Debian 池址：PF7 `_PF7_DEBIAN_HOSTS` 明确列为"下游重打包源"，写进 conandata 直接判 P0。
- `www.munted.org.uk`：包内 README 自述已停服。
- GitHub/GitLab 镜像：上游无官方 git 托管，**实测没有**此类址 ⇒ 不猜 URL。
- 任何加速前缀（`gh-proxy`/`ghfast`/`kkgithub`/…）：PF7 黑名单，且官方址三采全绿，无理由使用。
- 为过校验改哈希：未发生，也未需要 —— 官方值与核验值本就相同。

---

## 6. W0 依赖核验台账

| 依赖来源 | 结论 | 判定依据（一手） |
|---|---|---|
| `m4/pcre.m4` → `--with-pcre` | **不引入 pcre2** | `AC_ARG_WITH(pcre,...)` 缺省分支 `with_pcre=no`；实测 configure 输出 `checking for --with-pcre... no`、`configure: checking for PCRE...` 后无动作，生成 `Makefile` 里 `PCRE_LINK = ` 为空 |
| `configure.ac` → `LINUXINFO_PROG_PO4A` | **不引入 po4a** | 宏体是 `AC_CHECK_PROGS([PO4A],[po4a])` + `if USE_NLS=yes && PO4A 非空`，实测 `checking for po4a... no` → `USE_PO4A = no`，`po4a/Makefile` 落到空目标 `all-local-no:`；man 页 `po4a/linuxinfo.1` 官方件已自带 |
| `configure.ac` → `AM_GNU_GETTEXT([external])` | **不引入 gettext/libintl** | 实测 `checking for GNU gettext in libc... no`、`... in libintl... no`、`checking whether to use NLS... no`；配方再显式 `--disable-nls` 钉死，`Makefile` 里 `USE_NLS = no`、`LIBINTL =`、`LTLIBINTL =` 全空 |
| 系统头/函数 | 无外部包 | `AC_CHECK_HEADERS(unistd.h)`、`AC_CHECK_FUNCS(strstr uname)` 实测全 yes |

- `preflight_check.sh linuxinfo/4.2.3` → `[OK] 预检通过（无依赖需要检查）`（骨架期无声明依赖，符合预期）。
- `ohc-run.py recipe-search linuxinfo` → `⚠ 无相似配方（语料 6173 条）` ⇒ 首稿按模板 + 同族
  autotools-CLI 先例（`archives/a/aaphoto/0.45`、`archives/a/abnfgen/0.21` 的
  `_patch_configure_mktemp` 同款机制）抄形状，未手写整份配方。
- 判二进制可用性**没有**用通配 `conan list`（R35）；本包最终零 `requires()`，故无需下载探测。
- ⚠ 未把 `po4a` 伪装成 required，也未造 dummy 包 / 假头文件绕过任何依赖。

---

## 7. 出厂硬闸自检结果（`scripts/ohc/preflight.py`，PF1–PF9+R52）

对已推送的提交跑了一手自检：

```bash
python3 scripts/ohc/preflight.py . origin/main HEAD     # rc=1
✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  ——CI 将报 No packages to build（490 例）:
  archives/l/linuxinfo/README.md, archives/l/linuxinfo/commands.json,
  archives/l/linuxinfo/manifest.yaml
```

**除 PF9 外全部通过**：PF1 单包 / PF2 无二进制 / PF3 测试实质 + test_package 结构 /
PF4 依赖闸（本包零 requires）/ PF5 平台宏（两枚补丁均无 `__OHOS__`）/
PF6 共享前缀 / PF7 源 URL（conandata 只有官方 https 标量）/ PF8 配方静态
（settings 四项齐、slug、version 与目录一致、`commands.json` 的
`name`/`type=tool`/`versions[4.2.3].ref=linuxinfo/4.2.3` 对齐）/ R52 交叉校验。

### ⚠ PF9 这条是工具既有假阳性，**不要照它删文件**

PF8/R38 **要求** CLI 包在**软件级**目录放 `commands.json`（PF8 源码里就是
`pkg_dir / "commands.json"`，其报错文案还指名参照 `archives/a/abx/commands.json`），
而 PF9 用的是 `len(path.split('/')) < 5` ⇒ 任何软件级文件（`commands.json`/
`README.md`/`manifest.yaml`）都会被 PF9 判死。两条闸对**新包**天然互斥。

一手对照证据：对本仓**已合入 main** 的 `vamps/0.99.2` 提交（`ec60ece1`，即 main 顶端
`!11481` 那个 PR 的落地提交）跑同一套硬闸，得到**一模一样**的 PF9 命中：

```bash
python3 scripts/ohc/preflight.py . ec60ece1^ ec60ece1
✗ PF9 ... archives/v/vamps/README.md, archives/v/vamps/commands.json,
        archives/v/vamps/manifest.yaml
```

⇒ 说明"软件级三件套 + 版本目录"是本仓的正常形状，PF9 的 `<5` 判据没考虑这个形状。

**接力棒处置建议（按优先级，别自己动手改框架）**：
1. **不要**为了让 PF9 变绿而删 `commands.json` —— 那会把 PF9 的假阳性换成 PF8/R38 的**真**违规。
2. 建 PR 时若被这道闸拦住，这属于"确属官方形态的例外"，按 SKILL 的逃生口
   `--no-preflight`（并**在 PR 正文写清理由 + 上面 vamps 的对照证据**），
   或交主窗/CIW 定夺 —— 改 `scripts/ohc/preflight.py` 是框架改动，
   按 W2 必须**单独 PR**，不许夹在本包 PR 里。
3. 本条发现值得入登记表/广播给主窗（起草棒按分工**不碰表**，故只留此记录）。

---

**最终状态**

<!-- 起草棒收尾：本节由接力棒在 finish/submit 后回填（result.json 同源数字）。
     起草棒的事实边界到此为止：官方货源/W0/骨架/两枚补丁已成型并入库，
     **未执行 conan create，未执行 make，未跑 test_package，未建 PR，未碰平台与登记表**。 -->
- 起草棒（主理-68）：官方货源定性 ✅ / W0 依赖核验 ✅ / 配方骨架 + test_package 设计 ✅ /
  两枚补丁在纯净官方件上 dry-run + 实打 + configure rc=0 验证 ✅
- 未做：`conan create`、`conan-verify`、W3、W4 审计、PR、提审、登记表写入 —— **全部交接力棒**
---

## 9. 主理-73 收尾记录（2026-09-27，W3 红转绿 + 设备环境回归处置）

### 9.1 W3「fake test detected」根因与修复（L1d 假阳性，非真缺陷）

- 停工时判决：`[fail] L1d: test() method appears to be a fake test (echo/print/true only)`（旧
  w3-local-ci.log:437/448/462，读数存 `~/tmp/uc2/handoff/linuxinfo-4.2.3/park-readings.txt`）。
- 一手定位：`ci/conan/build_and_test.sh` 的 L1d 判据是对 test_package/conanfile.py **整文件逐行**
  `grep -qE "self\.run.*(echo|print|true)"`；本轮命中的不是可执行语句，而是注释行
  「PF3: test() 必须真的 self.run 被测包，不接受 print-only 空壳。」——同一行同时含 `self.run` 与 `print`
  两个词，被静态 grep 误伤（改前复现：grep 命中 conanfile.py:44，rc=0）。
- 修复：仅改写该注释（diff 1 行）；test() 的 `self.run` 与 test.sh 的 19 检查点**一字未动**
  （分母不变、无断言删除/缩小）。改后同一 grep rc=1（零命中）。
- 复验：新 w3-local-ci.log 判 `L1_RESULT=pass: test_package executed`，TC 段 `PASS=19 FAIL=0`，
  `L1e: Negative test confirmed — test genuinely depends on linuxinfo`。

### 9.2 设备环境回归：hnp bash 5.3 getcwd 全设备失败（非本包问题，本 PR 不含环境特判）

- 现象：conan create 在 configure 起手确定性失败（2/2 复现，~6s 即死）。第一条真实错误：
  `shell-init: error retrieving current directory: getcwd: cannot access parent directories` →
  `configure: error: working directory cannot be determined`。与 CONAN_HOME 路径是否含中文无关
  （home-主理-73-linuxinfo 与 home-z73-linuxinfo 双双失败，判别实验已做）。
- 根因链（逐环实证）：CI 框架 profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 把
  `CONFIG_SHELL`/`SHELL` 指到 `/data/service/hnp/bin/bash`（bash 5.3，hnp 管理，symlink 落点
  `../bash.org/bash_5.3/bin/bash`）；autoconf configure 头部（117-132 行）在 `CONFIG_SHELL` 非空时
  `exec $CONFIG_SHELL` 重执行自身；而该 bash 的 getcwd **现已全设备失败**——`$HOME` 根、`/data`、
  构建目录逐点实测 rc=1，同点 `/bin/sh -c pwd` 与 `/bin/pwd` 正常（微观复现留痕
  `~/tmp/uc2/z73-linuxinfo/logs/`）。上一棒 09-26 20:02 同链路成功且日志零 bash 报错
  ⇒ 该 bash 在 09-26 20:04 之后被设备侧更新/变更损坏。属基础设施回归，修复需设备 root/授权，
  本棒不动 `/data/service/hnp`（红线）。
- 处置：私有 overlay profile = `include(框架 profile)` + 覆盖 `[buildenv] CONFIG_SHELL=/bin/sh、
  SHELL=/bin/sh`，落 `~/tmp/uc2/z73-linuxinfo/profile-ohos-aarch64` 并注册为
  `$CONAN_HOME/profiles/ohos-aarch73`。conan create / conan-verify 显式用 `ohos-aarch73`；
  finish 的 W3（build_and_test.sh）经其既有 `CONAN_PROFILE` 环境钩子走同名 overlay。
  CONFIG_SHELL=/bin/sh 与 autoconf 无 CONFIG_SHELL 时的缺省路径一致，对健康环境零行为差异；
  CI 侧（buildbot，bash 健康）走原框架 profile，行为不变。
- 附带披露：finish 内嵌 step[4/10] conan-verify 走框架 profile，本轮 G2 的 `--build=missing`
  命中同 package_id 二进制缓存（overlay 与框架 profile 的 settings 全同 ⇒ package_id 相同），
  未真跑 configure 亦 PASS；两次独立 `conan-verify --profile ohos-aarch73` 全 PASS——step A
  （00:43，全新真构建，configure/make 在 /bin/sh 下完成）与 step C（00:47，缓存命中复验）。
  step A 完整日志：`~/tmp/uc2/z73-linuxinfo/logs/verify-a-20260927-004305.log`。

### 9.3 W3 绿读数（表 B 与正文四载体的同源来源）

- `reports/w3-local-ci.log`（2026-09-27 00:46，40149 B）
  sha256 = `57f5becdffb6341448354a534d641ea6246ec80e5d4127f4dd029751f754884a`；
  `[step]` 计数 47；`_RESULT=` 计数 8；`Calling build()` 命中 1；TC 段 `PASS=19 FAIL=0`。
- 判决原文：`L0_RESULT=pass: all checks passed` / `L1_RESULT=pass: test_package executed` /
  `L4_RESULT=warn: dangerous functions in patches`（补丁上下文行里的上游原文函数名，非新增）/ 
  `L5_RESULT=pass: bin/ has content`；`L1a/L1b/L1e` 全 ok。
- `checking whether we are cross compiling... no`（w3-local-ci.log:198）⇒ 显式三元组路线与
  E160 的冲突前提**实测不成立**，无需改刷 config.guess，全部既有证据继续有效。
- `.ci-result.json`：`exit_code=0`、`integrity_hash=0188f3013532e0bd`、`log_sha256` 与上同值。
- 非阻塞披露：①`L2_RESULT=skip`——工具 smoke test 调 `--version/--help`，本包只有 `-v/-h`
  （上游 main() 只认短参，行为如此）；②finish step7 报 **E305.kv root_cause/rec_approach 为空**
  ——仓库既有知识条目卫生问题，非本包引入，移交主窗/CIW；③finish step8 提示缺
  `reports/test-report.md`、`packaging/`、`.staging-verified`（提审前置件，归提审流程处理）；
  ④gen_summary 因框架 bug（`'str' object has no attribute 'append'`）未重生成 SUMMARY.md（非阻塞）。
- finish 对交付文本的改写清单（本轮与实测一致，属**真实**申报）：manifest `status` 由
  pending-build 经 harness 写成 `built-build`（双后缀畸形值，已订正为 `built`）；
  notes 尾部由 finish 追加 `编译结束: 2026-09-27 00:44` / `最终状态: built`；`build_date` 由本棒
  按实测填 `2026-09-27`。

**编译结束**: 2026-09-27 00:44
**最终状态**: built
