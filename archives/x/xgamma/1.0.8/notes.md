# xgamma 1.0.8 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 autoconf 预生成 `configure`，无需 autoreconf）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS 适配版 conan profile `ohos-aarch64`，os=OHOS/arch=armv8）
- 目标: HarmonyOS PC aarch64（B 机构建主机）
- CONAN_HOME: `~/tmp/ch/home-B-xgamma`（框架官方入口 `ci/conan/setup.sh` 初始化）

## 依赖
xgamma 是 X11 gamma 调节命令行工具，仅链接 Xlib + XFree86-VidModeExtension
（`configure.ac`: `PKG_CHECK_MODULES(XGAMMA, [x11 xxf86vm xproto >= 7.0.17])`；
`Makefile.am`: `xgamma_LDADD = $(XGAMMA_LIBS)`、`AM_CFLAGS = $(CWARNFLAGS)
$(XGAMMA_CFLAGS)`、`xgamma_SOURCES = xgamma.c`）。

全部取 ohpcd 已发布 OHOS armv8 二进制。**W0 实证口径**（不是通配 `conan list`，
R35）：`bash ci/scripts/preflight_check.sh xgamma/1.0.8 --deps "libx11/6.4.0
libxxf86vm/1.1.5 xorgproto/2025.1 libxcb/1.16 libxau/1.0.11"` → **5 个
`[OK] 已发布`** + `版本号未被占用: xgamma/1.0.8` → RC=0（本轮 2026-09-24 复跑）；
再 `conan install --build=never --requires=...`（`-pr:h -pr:b` 双指仓库 profile
文件）**实际下载**了 8 个包（libx11 / libxxf86vm / libxext / xorgproto / libxcb /
libxau / libxdmcp / xtrans），即二进制真实存在。

| 依赖 | 版本 | 来源 |
|---|---|---|
| libx11 | 6.4.0 | 直接依赖 |
| libxxf86vm | 1.1.5 | 直接依赖（其钉 libx11/6.4.0 + libxext/6.4.0 + xorgproto/2025.1，与本配方同源，无版本冲突） |
| xorgproto | 2025.1 | 直接依赖（提供 `xproto.pc`，configure 的 `xproto >= 7.0.17` 判定需要） |
| libxcb | 1.16 | 显式 run 依赖（libX11.so.6 的运行期 DT_NEEDED） |
| libxau | 1.0.11 | 显式 run 依赖 |

运行期 DT_NEEDED 闭包（`-version` 也需加载期解析全部 DT_NEEDED）：
`libXxf86vm.so.1 → libXext.so.6 + libX11.so.6`；
`libX11.so.6 → libxcb.so.1 + libXau.so.6`；`libxcb.so.1 → libXau.so.6 + libXdmcp.so.6`。

**归档名与本仓真实名对齐**（勿照台账猜）：登记表写 `x11,xproto,xxf86vm`，本仓
实际归档为 `libx11` / `xorgproto` / `libxxf86vm`（**没有 `xproto` 这个包**，
libxxf86vm 只有 **1.1.5**，无 1.2.x）。

不依赖编译环境预编译 X11 栈（`/storage/Users/currentUser/usr/local`）：CI worker
的栈可能完全没有 libX11（xeyes CI #28097 实证），全部走 conan 依赖。

## 构建系统选型（先验证再落笔）
上游 tarball 同时带 `configure.ac/Makefile.am`（及**预生成的 `configure`**）与
`meson.build`。评估 meson 路线可绕开 autoreconf/config.guess，但：
1. 显式 `--host=aarch64-unknown-linux-ohos` 后 config.guess（本 tarball 内
   `grep -c ohos` = **0**，完全不认 ohos）不被咨询；自带 config.sub 第 **2070**
   行（`| ohos* \`）与第 **2213** 行（`| linux-ohos*- )`）已支持，无需补丁；
2. 全部 X 应用先例（xev/xeyes/xterm/xclip）走 autotools，最小风险；
3. meson 需额外证明 OHOS worker 上 meson+ninja 工具链可用，收益不抵风险。

结论：选 **autotools**，0 补丁。

## 遇到的问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | 新 `CONAN_HOME=~/tmp/ch/home-B-xgamma` 起手只有 conancenter、无 ohpcd remote、profiles 目录空 | 新 home 未初始化 | 走框架官方入口 `zsh ci/conan/setup.sh`（禁用 conancenter、`conan remote add --force ohpcd <url>`）。注册后 `conan remote list` 见 `ohpcd ... Enabled: True`，`conan download libx11/6.4.0 -r=ohpcd --only-recipe` 取到 revision。**未手工硬写 remotes.json** |
| 2 | setup.sh 报 "Conan environment ready" 但 `conan profile list` 为空 | setup.sh 用 `conan profile import`，conan 2.29.1 的 `conan profile` 无 `import` 子命令，被 `\|\| true` 静默吞掉（xev 同款框架噪音） | 不需要命名 profile：框架 `scripts/ohc/conan_verify.py:557` 与 CI 一律用**仓库 profile 文件路径** `-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同>`。按该口径实测 `conan install` 正常解析 os=OHOS/arch=armv8。此为框架噪音，**不改框架** |
| 3 | `preflight_check.sh --deps "libx11,libxxf86vm,xorgproto"` 报「未发布: libx11,libxxf86vm,xorgproto」 | 自家传参格式错：该脚本要求 `--deps "dep1/ver1 dep2/ver2"`（**带版本、空格分隔**，且 `--deps` 要放在包名**之后**），逗号裸名被当成单个包名去查 | 改为 `--deps "libx11/6.4.0 libxxf86vm/1.1.5 xorgproto/2025.1"` → 3 个 `[OK] 已发布`。**教训：首错要读脚本 usage 行，别把参数错误当成依赖缺失去 `$P block`** |
| 4 | `conan download libxdmcp/1.2.5 --only-recipe` 报 `system acceleration policy not enabled` | 猜错版本号（制品仓实际是 libxdmcp/**1.1.5**）；该报错是 conan 对不存在 ref 的远端返回形态 | 不再手工猜：改由 `conan install --build=never` 让解析器给出真实闭包（1.1.5），libxdmcp 由 libxcb 传递引入，**本配方不显式声明** |
| 5 | 上游 x.org 源会 301 重定向 | `/archive/`、`/releases/` URL 需跟随重定向 | 取包一律 `curl -fL`；sha256 对**跟随重定向后真实下载到的 tarball**（170632 字节，`file` 判 gzip、tar 可解出完整源码树）计算。conandata.yml 只写官方 https，**不加镜像前缀**（R39） |
| 6 | **`conan-verify` G0–G4 全 PASS，但 `finish` 的 W3 在 `source()` 抛 `sha256 hash failed for '<8位hash>_xgamma-1.0.8.tar.gz'`** | CI 预下载把 x.org 源按「镜像优先」取包，三个镜像 URL 模板实测全 404，而它只按 `size>100` 判成功、不校验状态码与哈希 ⇒ 把 404 页当 tarball 喂给 conan | 把官方 URL 换成**同一官方主机上不被该正则命中的等价官方路径 `/pub/`**（详见下一节），sha256 一字未改 |

## W3 预下载把 x.org 源换成死镜像（本包真正的阻塞点）

### 症状
`conan-verify` 的 G0–G4 全 PASS，但 `finish` 的 W3 本地 CI 模拟在 `source()` 抛
`ConanException: sha256 hash failed for '<8 位 hash 前缀>_xgamma-1.0.8.tar.gz'`，
`Provided=` 是官方真值 `96ab71ea…`、`Computed=` 是另一个值；同一条日志末尾还会自陈
`[step] Pre-download: conandata.yml 已还原为官方 URL`。同族 xev 1.2.7 的实值是
文件 `2ea8f33b_xev-1.2.7.tar.gz`、`Computed=340c8464…`。

### 根因
`ci/conan/build_and_test.sh` 里有**两个互相独立**的 URL 改写机制，本包只被第二个命中：

1. **镜像改写**（第 1026-1027 行）由一张主机名白名单 `grep -qE` 把关，白名单里
   **没有 x.org**（只有 boost/github/gnu/gnome/kernel.org/pythonhosted/sourceforge/
   curl.se/jaist）⇒ 对本包**根本不触发**。其 python 里那段 x.org 镜像分支在这一
   步骤中是**死代码**。
2. **Pre-download**（第 1164 行起）只判 `[ -f "$CONANDATA" ]`，**没有白名单**，并自带
   `get_mirror_list()`：对 `^https?://xorg\.freedesktop\.org/(archive|releases)/`
   返回「三镜像优先、官方排最后」，下载成功判据只有一句 `if size > 100`——
   **既不校验 HTTP 状态码，也不校验 sha256**。

而它内置的三个 x.org 镜像 URL 模板**路径本身是错的**（实测对 xgamma 与同族 xeyes
一律 404，可作通用判据）：

| 镜像（按被尝试顺序） | HTTP | 响应体 | 响应体 sha256 |
|---|---|---|---|
| `mirror.csclub.uwaterloo.ca/x.org/…` | 404 | 162 B（nginx 404 HTML） | `340c8464c2007ce3…` |
| `www.mirrorservice.org/sites/ftp.x.org/pub/…` | 404 | 1796 B | `8f83da6a530f7c38…` |
| `mirrors.ircam.fr/pub/x.org/…` | 404 | 236 B | `9448f8a1159c9b14…` |

于是第 1 个镜像的 162 字节 404 页即被判成功、落盘为 `<md5(url)[:8]>_xgamma-1.0.8.tar.gz`
并 `content.replace(url, 'file://…')`，`source()` 拿 HTML 去算哈希必然不符。
**注意 `Computed` 值 `340c8464…` 就是那张 162 字节 404 页的哈希**——xev 与 xgamma 撞
的是同一个页面（同一 nginx 默认页，字节完全一致），这可以直接反证"投喂源是谁"。
另：conan 对"下载成功但校验失败"的项**不会**再回退到列表里的下一个 URL，所以列表形态
本身救不了它（见下）。

### 最小复现（不跑构建，直接用框架自己的代码）
把 `build_and_test.sh` 第 1191-1299 行的预下载 python 正文原样抽出，分别喂两种
conandata 形态：

```
旧写法（单值 /archive/）:
  [try 1/4.1/3] xgamma-1.0.8.tar.gz ← https://mirror.csclub.uwaterloo.ca/x.org/...
  [ok] xgamma-1.0.8.tar.gz (0KB) via mirror 1
  url: "file:///…/predl-old/8645905d_xgamma-1.0.8.tar.gz"   ← 162 B / sha=340c8464…  ⇒ sha256 必败
新写法（/pub/ 在前的官方列表）:
  c2036061_xgamma-1.0.8.tar.gz   170632 B   sha=96ab71ea…  == 官方真值            ⇒ PASS
  8645905d_xgamma-1.0.8.tar.gz        162 B sha=340c8464…  != 官方（列表第 2 项仍被投毒）
```
（复现脚本：`~/tmp/uc2/xgamma-p4-ab.sh`；镜像与官方域名逐个实测：
`~/tmp/uc2/xgamma-p1-urlpostmortem.sh`、`xgamma-p3-decisive.sh`。）

### 已试过的失败方案
1. **把 `sha256` 改成 `Computed=` 的值** —— 主动拒绝。那是 404 页的哈希，改它等于把
   错误页写进配方（P0 伪造源码身份），CI 与上游校验必失败。
2. **`www.x.org` 排在前面的"官方优先多域名列表"**（rgb 1.1.1 修复提交 `1ebb1f6fef`
   的形）—— **在 B 机不成立**。实测 `www.x.org` 与 `ftp.x.org` 三条下载栈全废：
   IPv4 `199.232.115.52:443` 连接被拒（curl rc=7）；IPv6 `2a04:4e42:5c::820` 可连但
   返回 301 跳向 `xorg.freedesktop.org`，且 TLS 报 **hostname mismatch**（证书 SAN 不
   含 `www.x.org`）。注意这是 **SAN 不匹配**，不是缺 CA——换任何信任库都救不了，
   curl / urllib(系统 CA) / urllib(certifi) 三套实测一致失败。
   ⇒ 该条目预下载阶段下不动、构建期也下不动，作兜底项等于没有。
3. **只把 `url` 改写成列表形态**（共享经验里对 E299 的记法）—— **不充分**。上面 A/B
   实测：列表里的 `/archive/` 项照样被预下载按镜像优先投毒。真正起作用的是**换到不被
   正则命中的官方路径**，而不是"改成列表"这个动作本身。
4. **往共享 `~/tmp/ch/dlcache` 预置已核 sha256 的官方 tarball**（`archives/x/xbanish/1.8`
   先例）—— 能让本地过闸，但它只改本机缓存、**不改变 CI worker 的行为**，等于把缺陷
   藏在本机；且 dlcache 跨任务共享，并发构建期写入会与别人的 conan 抢 `.dirty`。
   **未采用**。

### 最终方案
把 conandata 的官方 URL 换到**同一官方主机 `xorg.freedesktop.org` 上不被投毒正则命中的
等价官方路径 `/pub/`**（`/pub/individual/app/` 即 `ftp.x.org` 的标准布局，由同一官方
服务器提供），`/archive/` 作为第二条官方兜底保留；`sha256` 保持官方真值不动。
依据（本轮实测，B 机）：

| 官方 URL（都是 x.org 官方域，非代理前缀） | HTTP | 字节 | sha256 | 是否命中投毒正则 |
|---|---|---|---|---|
| `xorg.freedesktop.org/pub/individual/app/xgamma-1.0.8.tar.gz` | 200 | 170632 | `96ab71ea…` == 官方 | **否**（直连官方） |
| `xorg.freedesktop.org/archive/individual/app/xgamma-1.0.8.tar.gz` | 200 | 170632 | `96ab71ea…` == 官方 | 是 |
| `xorg.freedesktop.org/releases/individual/app/xgamma-1.0.8.tar.gz` | 200 | 170632 | `96ab71ea…` == 官方 | 是 |

`/pub/` 不命中 ⇒ `get_mirror_list()` 落到 `else: mirrors=[url]` ⇒ 预下载**直连官方**，
落盘即真包，`source()` 校验通过；且该判定只依赖 URL 字符串、与 worker 网络无关，
所以**本地 W3 与真实 CI 同源成立**（优于方案 4）。两条 URL 返回的是字节完全相同的
同一个官方包，互为可达性兜底。

### 适用边界
- 只对 `xorg.freedesktop.org/(archive|releases)/` 这一支有意义；`www.x.org`、`ftp.x.org`
  不命中改写，但在 **B 机不可达**（上面已实测），凡打算拿它们当兜底项的 x.org 包，
  接手时要先探一次可达性，别照搬 rgb 先例。
- `github.com/*` 一支会被改写成 `gh-proxy.com/…` 优先，但 gh-proxy 实测可用 ⇒ **不需要**
  照此改成列表，别做无谓修正。
- 这是**框架侧缺陷**（预下载不校验 HTTP 状态码/哈希、镜像 URL 模板路径写错），配方侧
  只能绕；框架修复应走单独 PR，本包不改 `ci/`、不改 `scripts/`。
- 知识库 **E299**（`sha256 hash failed for` + `404 Not Found`，
  `rec=classify-source-failure`）已收录该签名；本轮增量是把"绕开投毒的官方 `/pub/`
  路径"与"`/pub/` 与 `/archive/` 同字节"这两条实测补进证据链。

## 测试口径（本包最难处，含安全红线）

**安全红线**：xgamma 会**修改真机 X server 的 gamma**，而构建机就是用户在用的
机器 ⇒ 绝不允许留下被改掉的显示状态。做法是**逐条对照上游源码行号**证明断言
不可能触达 `XF86VidModeSetGamma`（第 252 行）：

| 断言 | 命令 | 源码位置 | 为什么不会改 gamma |
|---|---|---|---|
| 1 | `-version` | 第 126-129 行 `puts(PACKAGE_STRING); exit(EXIT_SUCCESS)` | 早于第 202 行 `XOpenDisplay`，进程根本没连服务器 |
| 2 | `--version` | 第 127 行 `!strcmp("--version", arg)` 同一分支 | 同上 |
| 3 | `-help` | 第 130-132 行 `Syntax(NULL, EXIT_SUCCESS)` → `exit` | 同上 |
| 4 | `-nosuchopt` | 第 190-193 行 `unrecognized argument` → `Syntax(NULL, EXIT_FAILURE)` | 同上 |
| 5 | `-gamma 0.05` | 第 144-149 行 `gam < GAMMA_MIN` → 打印边界 + `exit(EXIT_FAILURE)` | 取值域校验在参数解析循环内，早于建连 |
| 6 | `-gamma 99.0` | 第 144-149 行 `gam > GAMMA_MAX` 同一分支 | 同上 |
| 7 | `-gamma 1.0 -rgamma 1.0` | 第 154-155 行 `if (gam >= 0.0f) Syntax("cannot set both -gamma and -rgamma", 1)` | 互斥检查在解析循环内；即使 `-gamma 1.0` 合法也走不到建连 |
| 8 | `-gamma`（缺值） | 第 139-140 行 `if (++i >= argc) Syntax("-gamma requires an argument", 1)` | 同上 |
| 9 | 裸 `xgamma` | 第 202-205 行建连失败分支；成功则第 245-249 行 `else { /* Not changing gamma, all done */ ret = EXIT_SUCCESS; goto finish; }` | **上游默认行为即只读**：不带 gamma 选项时只做 `XF86VidModeGetGamma`，`goto finish` 跳过第 252 行 SetGamma。本条仅在本机确认无可达 X server（`DISPLAY` 未设置且 `/tmp/.X11-unix/X*` 不存在）时执行并断言上游逐字串 `unable to open display`；有 display 则记 skipped（不猜服务端 VidMode 扩展状态） |

- 上游无自动化测试（见 `test_package/MANIFEST.yml` 五条审计），规则要求 test_package
  真实执行被测二进制并对可观察行为断言（R34），声明数 ≤ 实测数（rule4）。
- 与同族先例的差异：xev/xeyes 只能靠 `-version/-help`（早于 `XOpenDisplay`）做无头
  真跑；xgamma 的**取值域 / 互斥 / 缺值**三条属于真正的领域逻辑（`GAMMA_MIN 0.1f` /
  `GAMMA_MAX 10.0f` 常量与选项互斥矩阵），同样早于建连，故无头环境也能覆盖到包的核心
  判定，而不只是打印字符串。断言同时校验错误串里打印出的边界 `0.100` / `10.000`
  （`%6.3f` 格式化），使其具有判别力——若常量或格式化被改，断言会失败。
- `PACKAGE_STRING = "xgamma 1.0.8"`（`AC_INIT([xgamma],[1.0.8])` 生成的 config.h；
  `xgamma.c` 第 25-27 行 `#ifdef HAVE_CONFIG_H #include "config.h"`，automake 的
  `@DEFAULT_INCLUDES@` 提供 `-DHAVE_CONFIG_H`）。
- 无头环境的第 9 条断言错误串**逐字取自上游** 第 203-204 行：
  `fprintf (stderr, "%s:  unable to open display '%s'\n", ...)`（注意冒号后是两个空格）。
- 运行期寻库照 xev：conanrun 环境 LD_LIBRARY_PATH + test_package 从依赖包取实体 .so
  绝对路径 `LD_PRELOAD`（依赖序 libXau→libXdmcp→libxcb→libX11→libXext→libXxf86vm），
  POSIX sh 脚本以 HMBS 注入 `SHELL=/bin/sh` 执行。

**未覆盖（如实声明，不并入通过）**：
gamma 读写的服务端往返路径（第 209-228 行 `XF86VidModeQueryVersion` /
`QueryExtension` 版本门 + 第 230-235 行 GetGamma + 第 252-265 行 SetGamma 与读回
打印）。原因两条：①需真实 X server 且服务端加载 XFree86-VidModeExtension ≥ 2.0，
构建机 `DISPLAY` 未设置、无 `/tmp/.X11-unix`，不可执行；②`SetGamma` 属真机显示
副作用，按安全红线主动不执行。该分母是**静态**的：上游 9 个可执行代码路径中本套件
注册并执行了 9 个早于/只读于建连的路径，服务端往返那一支**不在这 9 条之内**，
故不构成"少报"，只是本包能力面的边界。

## 峰值 RSS（手册/05 ⓓ）

工具存在：`$HOME/Desktop/huawei/经验文档/tools/memcap-run.py`（同步仓的 tools 目录）。
**订正**：本节此前写「本机构架未提供 memcap-run.py（find 全盘无该脚本）」——该结论
不成立，当时只在 worktree 的 `scripts/` 与 `ci/` 下找过，未覆盖同步仓路径。本轮按
手册/05 ⓓ 用该工具真跑 `--probe` 取得实测值。

测法（复刻 `conan test_package` 成功那次的运行期环境：`LD_PRELOAD` 取
`reports/conan-create.log` 第 **160** 行 recipe 自己算出的 6 项 .so 绝对路径链
（同一条链在 `reports/w3-local-ci.log` 第 **425** 行亦打出），
`LD_LIBRARY_PATH` 取这些 .so 的 dirname + 包内 bin；只给 LD_PRELOAD 会因
libXau/libXdmcp 解析不到而 rc=127）。先证明被测二进制在该变量下真能跑：
`xgamma -version` → `xgamma 1.0.8`，rc=0。
（旧文本此处写作「conan-create.log 第 346 行」——该文件只有 233 行，属行号错位，已按
`grep -n LD_PRELOAD` 的实测位置订正。）

xgamma **不接受任何输入文件**（命令行只有开关与浮点参数），输入规模恒为 0，
故 `--scale` 取 1、不做外推。实测（`MEMCAP[probe] peak=… budget=… rc=…`）：

| 探针 | 命令 | 实测峰值 | rc |
|---|---|---|---|
| A | `xgamma -version`（最小路径，早于 `XOpenDisplay`） | `peak=2MB` | 0 |
| B | `xgamma -help`（Syntax 路径） | `peak=1MB` | 0 |
| C | `xgamma -gamma 0.05`（GAMMA_MIN 校验路径） | `peak=2MB` | 1（预期：越界即拒） |
| D | 全量 9 条断言套件 `test_xgamma.sh` | **`peak=9MB`** | 0 |

套件那条同时打出 `[summary] discovered=9 passed=9 skipped=0 failed=0`。

- **同一套件的第二轮独立实测**：W4 审计在 B 机复刻同一运行期环境重跑交付版
  `test_xgamma.sh`，得 `MEMCAP[probe] peak=10MB budget=0MB rc=0`，同时
  `[summary] discovered=9 passed=9 skipped=0 failed=0` 与本窗逐项相同
  （判决件 `.ci-result` 外的独立复探，非本窗第 4 次采样）。
- **登记值 `max_rss_mb: 10`（取两次独立实测的上界，不挑单点掩盖抖动）**：本窗探针 D
  `9MB` 与审计复探 `10MB` 各一次，差 1MB 属 `memcap-run.py --probe` 采样间隔抖动
  （旧登记值 9 是单点值，会被后人当硬上界用，故改判为观测上界 10）。
  `manifest.yaml`、`test_package/MANIFEST.yml` 与本节三处已同步为 10。
- 槽位门槛：短单 `--mem 2500`，实测上界 10MB ≪ 2500MB，无 OOM 风险；该包也不可能随输入
  增长（无输入）。

## 五维测试数字账本

| 维度 | 值 | 依据 |
|---|---|---|
| N_static（上游源码静态计数，行首锚定，逐文件） | **0** | 本轮对解包后的官方 1.0.8 源码树逐项复跑：`grep -cE '^[[:space:]]*assert\(' xgamma.c` = **0**；`Makefile.am` 行首锚定 `TESTS`/`check_PROGRAMS`/`check-local` = **0**；`meson.build` 行首锚定 `test(` = **0**；`configure.ac` 无 `AC_CONFIG_TESTDIR`；`find -type d -name tests\|test` = **0**；`find -name '*_test.[ch]' -o -name 'test_*.[ch]'` = **0**。另按"少报"四类资产补查：`demo/examples` 目录 **0**、`*RUNTEST*` 脚本 **0**、`*/res` 语料目录 **0**，源码树子目录仅 `man/` |
| N_registered（ctest/meson/TESTS 注册数） | **0** | `Makefile.am` 无 `TESTS`/`check_PROGRAMS`；`Makefile.in` 命中的第 824-825 行 `check-am:`/`check:` 是 automake 样板规则、不含用例；`meson.build` 无 `test()`；`configure.ac` 无测试宏 |
| N_executed（真机实测：通过/失败/跳过/disabled 四项分列） | **9 / 通过 9 / 失败 0 / 跳过 0 / disabled 0** | `test_xgamma.sh` 实跑汇总行 `[summary] discovered=9 passed=9 skipped=0 failed=0`（`conan-verify` G2 与本轮 memcap 探针 D 两次独立跑到同值）；第 9 条走"无可达 X server"分支并真断言，未记 skipped |
| 未执行分类与原因 | gamma 服务端往返（Query/Get/Set，第 209-265 行）：①无 X server 与 VidMode 扩展；②SetGamma 属真机显示副作用，安全红线主动不执行 | 见「测试口径」。**不计入通过、也不从分母静默删除** |
| N_consumer（+ N_assertion 括注） | **9**（括注 N_assertion=**20**） | 9 个 case 各含退出码判定 + 上游逐字串判定。20 的推导：`grep -oE 'rc -(eq\|ne) 0'` = **9** 处退出码判定，`grep -oE 'grep -qi? '` = **11** 处输出串判定（含 test 5 的嵌套边界串 `0.100` / `10.000` 两处），9+11=**20** |

声明数 ≤ 实测数：N_static=0 ≤ N_executed=9；`N_consumer=9` 与 `N_assertion=20` 同源写在
`notes.md`、`test_package/MANIFEST.yml`、`manifest.yaml`、消费者日志与本报告五处。

## 验证结果

- `bash ci/scripts/preflight_check.sh xgamma/1.0.8 --deps "<5 个带版本依赖>"` →
  **5 个 `[OK] 已发布`** + `版本号未被占用` → **RC=0**（W0 精确复查）
- `python3 scripts/ohc-run.py recipe-search xgamma` → `⚠️ 无相似配方（语料 6173 条）` → **RC=0**
- `python3 scripts/ohc-run.py conan-verify xgamma 1.0.8` → **G0 PASS / G1 PASS /
  G2 PASS / G3 PASS / G4 PASS**，`✅ 配方验证通过: xgamma 1.0.8`，**VERIFY_RC=0**
  （改 conandata 后重跑，非沿用旧 PASS）
- 真编译自查（防 binary cache 伪装成"验证通过"）：真实物编译证据在
  `reports/w3-local-ci.log`——第 **208** 行 `xgamma/1.0.8: Building from source`、
  第 **218** 行 `xgamma/1.0.8: Calling build()`（两项各命中 **1** 次：
  `grep -c 'Building from source'` = 1、`grep -c 'Calling build('` = 1；其上是第 **207**
  行 `Installing package xgamma/1.0.8 (9 of 9)`、其下是第 **215** 行 `Generators folder:`），
  test_package 真实执行并打出
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,…,"discovered":9,"passedCount":9,"skipped":0}`
  （第 **496** 行）。该日志 45 处 `- Cache` 里属 xgamma 的三条是第 **167**、**378** 行
  （**配方 revision 级**条目，不含二进制 id）与第 **398** 行（第 208 行那次编译**完成并
  打包之后**的再安装才命中二进制缓存），故 45 处无一条表示"本包没编译"，其余 42 处属
  依赖包（libx11/libxxf86vm/…）
- **`reports/conan-create.log` 不能作为"真编译"证据（本轮订正）**：该文件实测
  `grep -c 'Building from source'` = **0**、`grep -c 'Calling build('` = **0**、
  `grep -c -- '- Cache'` = **44**，且其第 **63 / 84 / 113 / 133** 行把
  `xgamma/1.0.8@ohpcd/stable`（含二进制包 id）明确列为 `- Cache`、第 **97 / 146** 行为
  `Already installed! (7 of 7)` —— 它是 `conan test` 复跑，**被测二进制恰恰命中缓存**，
  与"非缓存真编译"的结论相反。该日志的有效用途只有一个：证明 test_package 断言可重放
  （测试段第 167-231 行、汇总行第 229 行）。本节与 `reports/test-report.md` 旧文把
  "1 次 / 1 次 / 45 处全属依赖"归给该文件属引用错位，已全部改指 `w3-local-ci.log`
- **上述真编译证据的适用边界（不夸大）**：两份日志里 `Calling source` 计数均为 **0**
  （`grep -c 'Calling source'` 对 `w3-local-ci.log` 与 `conan-create.log` 都返回 0）
  ⇒ conan 复用了已有的源码目录，所以这两条证据支撑的只是"**编译 / 链接 / 测试真实执行**"，
  **不含**"源码按 conandata 重新获取"；后者（源码获取的可复现性）由本笔记「最终方案」一节的
  两条官方 URL 取证 + 独立 `curl` / `cmp` / `sha256sum` 实测提供，两件事分开写、不互相顶替
- 两处**既存降级口径**（E478 家族，不算本包缺陷，但如实登记，**未执行不并入通过、分母不删**）：
  ① `reports/w3-local-ci.log` 第 **511** 行 `[warn] L2: xgamma --version/--help failed
  (non-blocking)` → 第 **515** 行 `L2_RESULT=skip: xgamma version/help failed`——框架
  smoke test 判据是**裸跑** `xgamma --version` / `--help`（不带 test_package 的
  LD_PRELOAD/LD_LIBRARY_PATH 运行库注入），在该机上取不到 `libXxf86vm.so.1` 而失败；
  这与本套件第 2 条断言（同一二进制、带运行期注入、第 435-437 行 PASS）不是同一执行条件。
  ② 第 **503** 行 `[ok] L1c: Upstream official tests (make check/ctest) executed in build
  phase` 是**框架样板输出**，其判据只是"构建阶段跑过 make check"，不代表存在用例；
  同一日志第 **498** 行 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",…,"discovered":0,
  "executed":0,…}` 才是本包的真实上游测试状况（0 用例），与 `test_package/MANIFEST.yml`
  的 `upstream_tests_exist: false`、账本 `N_static=0 / N_registered=0` 一致 ⇒ L1c 的 ok
  不可读作"上游有测试被执行"
- W3：`.ci-result.json` 的判决与时效见本目录 `reports/`（由 `finish` 落盘）
- 骨架提交 `776140782`（配方骨架 + 无头 9 断言 test_package）；本轮交付提交是其后的
  conandata 修复 + 账本/探针补全，sha 由 git 记录

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方，conan 依赖 libx11+libxxf86vm+xorgproto，XGAMMA_CFLAGS/XGAMMA_LIBS 交由 AutotoolsDeps + 真实 pkg-config 解析，package() 自签 bin/xgamma |
| conandata.yml | 两条 x.org 官方 URL（`/pub/` 在前规避 W3 投毒）+ 官方 sha256 原值（无镜像前缀、无本地路径注入） |
| test_package/conanfile.py + test_xgamma.sh | 无头真跑 9 条命令行断言（含 gamma 取值域/互斥/缺值领域逻辑）+ LD_PRELOAD 运行期兜底 |
| test_package/MANIFEST.yml | 上游无测试审计（5 条）+ test_package_test_count=9 / upstream_test_count=0 / assertion_count=20 + max_rss_mb=10（两次独立实测 9MB / 10MB 的上界） |
| reports/test-report.md | 测试五维账本与逐条原始证据（计数口径 / Results / Raw evidence 带行号 / Not covered / Integrity） |
| manifest.yaml（版本级/软件级） | 归档信息与版本索引 |
| README.md（软件级） | 软件描述与已知平台问题 |
| commands.json（软件级） | R38 命令行工具声明（type=tool、binary=true）。**binary=true 的实测依据**：`find ~/tmp/ch/home-B-xgamma/p/b/xgamm*/p/bin -type f` 命中 3 个包目录下的 `bin/xgamma`，各 27008 字节、`file` 判 `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`、三者 sha256 前缀同为 `b745b7573e7113b7`；配方 `conanfile.py:60 package_type = "application"`、`:214 self.cpp_info.bindirs = ["bin"]`，W3 `reports/w3-local-ci.log:506` `[ok] L5: bin/ has content`。与先例 `archives/x/xeyes/commands.json` 的 `binary: true` 对齐（模板 `templates/commands.json.template:9` 的 false 只是默认值） |
| patches/ | 空（无需补丁） |
---

**编译结束**: 2026-09-24 02:49
**最终状态**: built
