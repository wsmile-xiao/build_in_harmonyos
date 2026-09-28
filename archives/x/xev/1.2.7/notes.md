# xev 1.2.7 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 autoconf 2.73 预生成 configure）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS 适配版 conan profile ohos-aarch64，os=OHOS/arch=armv8）
- 目标: HarmonyOS PC aarch64

## 依赖
xev 是 X11 事件打印程序，仅链接 Xlib + XRandR（「configure.ac」:
「PKG_CHECK_MODULES(XEV, [xrandr >= 1.2 x11 xproto >= 7.0.22])」；「Makefile.am」:
「xev_LDADD = $(XEV_LIBS)」、「AM_CFLAGS = $(XEV_CFLAGS)」、「xev_SOURCES = xev.c」）。

全部取 ohpcd 已发布 OHOS armv8 二进制（W0 预检「--only-recipe」RC=0）：

| 依赖 | 版本 | 来源 |
|---|---|---|
| libx11 | 6.4.0 | 直接依赖 |
| libxrandr | 1.5.5.1 | 直接依赖（其钉 libxext/6.4.0 + libxrender/0.9.12 + xorgproto/2025.1） |
| libxcb | 1.16 | 显式 run 依赖（libX11.so.6 的运行期 DT_NEEDED） |
| libxau | 1.0.11 | 显式 run 依赖 |

运行期 DT_NEEDED 闭包（加载期需解析全部 DT_NEEDED）：
「libXrandr.so.2 → libX11.so.6 + libXext.so.6 + libXrender.so.1」；
「libX11.so.6 → libxcb.so.1 + libXau.so.6」；「libxcb.so.1 → libXau.so.6 + libXdmcp.so.6」。

## 构建系统选型（先验证再落笔）
上游 tarball 同时带「configure.ac/Makefile.am」（及**预生成的 configure**）与
「meson.build」。评估 meson 路线可绕开 autoreconf/config.guess，但：
1. 本机缺 automake（init-build 的 check_env 因此崩，见下）——而 xev 自带
   autoconf 2.73 生成的 configure，autotools 路线**根本不需要 automake/autoconf**；
2. 显式「--host=aarch64-unknown-linux-ohos」后 config.guess（不支持 ohos）不被
   咨询，config.sub（xev 自带，支持「ohos*」/「linux-ohos*」）通过；
3. 全部 X 应用先例（xeyes/xterm/xclip）走 autotools，最小风险。

结论：选 **autotools**。meson 需额外证明 OHOS worker 上 meson+ninja 工具链可用，
收益不抵风险。

## 遇到的问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | CONAN_HOME=~/tmp/ch/home-B-xev 初始只有 conancenter、无 ohpcd，profiles 空 | 新建 home 未初始化 | 走框架官方入口「ci/conan/setup.sh」（禁用 conancenter、conan remote add ohpcd、导入仓库 profile）。未手工硬写 remotes.json |
| 2 | setup.sh 报“Conan environment ready”但「conan profile list」为空、「conan profile show -pr ohos-aarch64」报 Profile not found | setup.sh 用「conan profile import」——conan 2.29.1 的 conan profile **无 import 子命令**（只有 detect/list/path/show），被「|| true」静默吞掉 | 无需命名 profile：框架（conan_verify.py）与参考 home 一律用**仓库 profile 文件路径**「-pr:h=ci/conan/profiles/ohos-aarch64」解析。「conan profile show -pr:h=<file>」验证正常，os=OHOS 有效。此为框架噪音，不改框架 |
| 3 | ohc-run.py init-build 末尾崩溃：check_env.py:33「NameError: name 'e' is not defined」 | _check_cmd 探测缺失的 automake 时 subprocess.run 抛 FileNotFoundError，except 分支误引用未定义 e（框架潜在 bug，被本机缺 automake 触发） | init-build 崩溃点在 scaffold 之后（manifest.yaml/notes.md 已生成）；check_env() 仅被 init-build / check-env 调用，**不影响 conan-verify / finish**。绕过 init-build，直接填充配方并跑 conan-verify。上报框架噪音，不改 scripts/ |
| 4 | W3 预下载步骤把源码 URL 原地改写为本地路径型 URL，且**不校验 HTTP 状态码、不校验 sha256**（成功判据只有 size>100B）⇒ 命中死镜像时 source() 只会收到 162 字节的 404 错误页；上一轮该缺陷叠加 www.x.org 不可用，导致那次 W3 **根本没有调用 source()**（旧 reports/w3-local-ci.log 里 Calling source 计数 = 0，实测复核确认），即那次绿只证明「能编译」，不证明「按 conandata 能取到正确源码」 | 框架预下载缺陷（属单独 PR 范畴，不在本包修）：它对 xorg.freedesktop.org 的 archive/ 与 releases/ 两个路径段走「镜像优先」重试 ⇒ archive/ 那条会被换成一页 162 字节的 404 页并算作下载成功；www.x.org 在 B 机**确定性不可用**（curl: (60) SSL: no alternative certificate subject name matches target host name 'www.x.org'，http=000 / size=0，2026-09-24 03:16 复现，非抖动）⇒ 不得充当首条依赖 URL | sources.url 改为**同一官方主机 xorg.freedesktop.org 的两条官方路径**：pub/ 在前（不命中那条路径正则 ⇒ 预下载直连官方取到 180306 字节真包）、archive/ 兜底；**删掉 www.x.org 那条**。两条都是官方原始 URL，无第三方代理前缀、无本地路径型 URL ⇒ 符合 R39。conan tools.files.download() 对 URL 列表按序逐条尝试且**逐条**校验 sha256 ⇒ 首条即命中真包。**sha256 一个字节未改**。随后用 conan remove xev/1.2.7 -c 强制冷验，新日志 Calling source 命中 1 次（取证见下节） |

## W3 预下载投喂 404 页取证与本轮强制冷验

### 已证事实（逐条附命令与实测）
1. **www.x.org 在 B 机确定性不可用，不能当首条依赖 URL**。
   命令（B 机，2026-09-24 03:16）：
   「curl -sS -o ~/tmp/uc2/xev-cold/probe2.bin -w 'http=%{http_code} size=%{size_download}\n' https://www.x.org/archive/individual/app/xev-1.2.7.tar.gz」
   逐字结果：「curl: (60) SSL: no alternative certificate subject name matches target host name 'www.x.org'」
   ＋「http=000 size=0」「rc=60」⇒ 这是 TLS 主机名不匹配的**确定性失败**（不是网络抖动），
   与上一轮旧 w3 日志里三条「[fail] size=0, http=0:0」一致。留作首条 URL 会让取源依赖一个取不到的地址。
2. **两条官方 xorg.freedesktop.org 路径本轮实测均可直连且逐位等价于交付哈希**（同主机、同尺寸）：
   - 「https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz」⇒
     「http=200 redirects=0 size=180306」「gzip compressed data」
     「e75e35e225acdfe648a73e75aedabccf47f46bdab6590f43428be97b2876b94e」（= conandata 值，未改动）
   - 「https://xorg.freedesktop.org/archive/individual/app/xev-1.2.7.tar.gz」⇒ 同上「http=200 size=180306」同哈希。
   ⇒ 任何「两个域名互相当一致证据」式的论证都不成立，本包的排序依据改成两条实测事实：
   可达性（上面的 curl 逐字结果）＋ 是否命中框架预下载的那条路径正则。
   排序理由改成「pub/ 不命中框架预下载的那条路径正则 ⇒ 直连官方」，机理见下。
3. **上一轮那次 W3 绿不绑定源码获取**：旧 reports/w3-local-ci.log 里
   「grep -c 'Calling source'」= **0**（本轮开工时实测记录在
   「~/tmp/uc2/xev-cold/01-scene.txt」），即 conan 复用了此前已解出的 source 目录、只证明了编译。

### 框架预下载机理（读源码定位，不改框架）
「ci/conan/build_and_test.sh」预下载段（Python 块，约 1195–1300 行）行为：
- 「url_pattern = r'(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)'」连**注释**一起抓
  ⇒ 故 conandata.yml 的注释里刻意不写带协议的 URL 串。
- 「get_mirror_list()」对「^https?://xorg\.freedesktop\.org/(archive|releases)/」返回
  「[三个站点镜像, 原始 URL]」的**镜像优先**列表；「pub/」不命中该正则 ⇒ 列表只有官方 URL 本身。
- 成功判据只有「if size > 100」⇒ 镜像返回的 162 字节 404 页被判为「下载成功」，
  再把命中的 URL 原地改写成本地路径型 URL（本轮新日志第 103 行是该步的收尾打印）。
- conan 侧（「conan/tools/files/files.py」＋「conan/internal/rest/caching_file_downloader.py」的
  「_do_download」）对 URL 列表**按序逐条**尝试、且**每条各自**校验 sha256：任一条失败只 warn 后
  落到下一条，只有最后一条失败才 raise ⇒ 把 pub/ 排第一即保证第一轮命中真包。

### 本轮强制冷验（结论：源码获取已绑定 conandata）
取证脚本与日志留在「~/tmp/uc2/xev-cold/」（01-scene.txt / 02-url-probe.txt / 20-run.txt）。

1. 换 conandata 后先跑「ohc-run.py conan-verify xev 1.2.7」⇒ G0–G4 全 PASS、RC=0，
   该轮 conan create 转写里出现冷取两行（原文当时在「reports/conan-create.log」第 122/123 行；
   该文件随后被 finish 内部再跑一次覆盖，故此处引**留存的定稿快照**
   「~/tmp/uc2/xev-cold/20-run.txt」第 17/18 行，逐字）：
   「xev/1.2.7@ohpcd/stable: Calling source() in …/p/xev6d29aa59a5def/s」
   「xev/1.2.7@ohpcd/stable: Sources correctly downloaded from https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz」
   ⇒ **首条官方 pub/ URL 冷取源码并通过 sha256 校验**（校验不过 conan 会直接 raise）。
2. 再按 conan 官方手段「conan remove xev/1.2.7 -c」（Remove summary 两行 revision 均
   「Removed recipe and all binaries」）清掉本任务 home 内的 xev 配方缓存，使 W3 必须重新取源，
   然后「sh ~/tmp/uc2/gate.sh」（GATE_PASS，MemAvailable=16172MB）＋
   「sh ~/tmp/uc2/build-slot.sh --kind short --wait 3600 --mem 2500 -- python3 scripts/ohc-run.py finish xev 1.2.7 built」。
3. 新「reports/w3-local-ci.log」（523 行，绑定 .ci-result integrity_hash
   「f08ae7bf497cb201」）实测：
   - 「grep -c 'Calling source'」= **1** ⇒ 本轮 W3 **真的调用了 source()**
   - 第 99 行「found 2 source URL(s)」；第 100–101 行
     「[try 1/1.1/3] xev-1.2.7.tar.gz ← https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz...」
     「[ok] xev-1.2.7.tar.gz (176KB) via mirror 1」⇒ 176KB = 180306 字节真包；
     此处「mirror 1」是框架重试循环的**序号标签**（pub/ 不命中路径正则，候选列表里只有官方 URL
     本身，序号 1 即官方源），不是使用了镜像前缀。
   - 第 102 行「[cached] xev-1.2.7.tar.gz (0KB)」⇒ 第二条 archive/ 命中了上一轮残留的 162 字节
     404 页缓存（正是该缺陷的现场），印证「必须把 pub/ 排第一」。
   - 第 207 行「xev/1.2.7: Calling source() in …/p/xev5c6205c0ea6f0/s」
   - 第 208 行「Sources correctly downloaded from …/predl_cache/2e2a1c23_xev-1.2.7.tar.gz」
     （2e2a1c23 = 首条 pub/ URL 的预下载落盘名，内容即 180306 字节真包，conan 逐条校验通过）
   - 第 495 行「[ok] xev/1.2.7 — conan create passed」，第 522 行
     「[step] All packages built and tested successfully ✅」
4. 交付态复核（每次 verify/finish 之后都重跑）：对 conandata.yml 与 manifest.yaml 统计
   「本地路径型 URL / 第三方代理前缀 / 境外站点镜像域名」三类字面量，命中数均为 **0**
   （检查命令与正则记在取证脚本 「~/tmp/uc2/xev-cold/20-cold-finish.sh」第 5 步，可直接复跑；
   此处刻意不把该正则原文抄进交付件，以免归档树内出现被检字面量）、
   「patch_generation:」「patch_classification:」残留 = **0**、
   被跟踪的 .bak/.orig/备份后缀 = **0**；
   conandata.yml mtime = 2026-09-24 03:27:53.336442031（W3 收尾还原官方 URL 的时刻）、
   .ci-result.json 内 timestamp = 2026-09-24T03:27:53.370249 ⇒ **证据晚于配方文件**。
5. 遗留非阻塞事实（如实记录，未动手脚）：finish 的 Step 3「G0 干净构建验证」打印
   「❌ G0: 找不到原始 tarball」（clean_verify 只在仓库根/「.build-context-xev-1.2.7」找包，
   本任务两处均无包，故上一轮「~/tmp/uc2/xev-finish.log」第 35 行同样是这条；属既有环境/框架
   噪音，不在本包修，也不与上面 W3 的取源验证混为一谈）。

## 测试口径（本包最难处）
上游 0 自动化测试（实测取证见下节命令与结果）。规则要求 test_package 真实执行被测二进制、
正文声明数 ≤ 实测数。

- 实证「xev.c」的「-version」（case 'v' → puts(PACKAGE_STRING); exit(0)，源码第 1352 行）、
  「--version」（case '-' 同 puts，源码第 1363 行）、「-help」/「--help」（usage(NULL, EXIT_SUCCESS)）、
  未识别选项（usage(NULL, EXIT_FAILURE)）**全部早于第 1384 行「dpy = XOpenDisplay(displayname);」**
  → 只要动态库能加载，无 X server 也能真跑（同 xeyes「-version/-help」先例机制）。
- PACKAGE_STRING = "xev 1.2.7"（「AC_INIT([xev],[1.2.7])」生成的 config.h）。
- 运行期寻库照 xeyes：conanrun 环境 LD_LIBRARY_PATH + test_package 从依赖包取
  实体 .so 绝对路径 LD_PRELOAD（依赖序 libXau→libXdmcp→libxcb→libX11→libXext→
  libXrender→libXrandr），POSIX sh 脚本以 HMBS 注入「SHELL=/bin/sh」执行。
- **未覆盖**：GUI 事件循环路径（XNextEvent 主循环、do_RRNotify_* 等 XRandR
  事件处理）需真实 X server + 用户交互，无头 CI 无法执行，本 test_package 不测。

## N_static / N_registered 实测取证（命令与逐字结果）
取证目录 = **本轮 Calling source 冷取**解出的上游源码树
「~/tmp/ch/home-B-xev/p/xev5c6205c0ea6f0/s」（即新 w3 日志第 207 行那个目录；含 xev.c 48207 字节，
「sha256sum xev.c」= fb6ecd81084d83751ba0e3f3ca0ee6f27cfdf8e8e21f0b585c9c29848a5aaf63）。
下表命令于 2026-09-24 03:3x 在该目录内重跑（脚本「~/tmp/uc2/xev-cold/40-measure.sh」），
均在 Bash 单行给出，结果逐字记录（rc=1 表示 grep 无匹配）：

| 断言 | 命令 | 实测结果 |
|---|---|---|
| 上游无 assert 型用例（行首锚定） | 「grep -cE '^[[:space:]]*assert[[:space:]]*\(' xev.c」 | **0** |
| 上游全文 assert( 计数 | 「grep -oE 'assert[[:space:]]*\(' xev.c \| wc -l」 | **0** |
| 无 tests/ 或 test/ 目录 | 「find . -maxdepth 2 -type d \( -name tests -o -name test \)」 | 无输出（rc=0，命中 0 个） |
| 无 *_test.c / test_*.c 源文件 | 「find . -maxdepth 2 -type f \( -name '*_test.c' -o -name 'test_*.c' \)」 | 无输出（0 个） |
| Makefile.am 无 TESTS/check 目标 | 「grep -nE 'TESTS\|check' Makefile.am」 | 无匹配，**rc=1**（唯一 SUBDIRS 行为「SUBDIRS = man」） |
| Makefile.in 无 TESTS 变量 | 「grep -nE 'TESTS *=' Makefile.in」 | 无匹配（automake 仅生成空壳「check: check-recursive」@825、「check-am: all-am」@824，无用例注册） |
| configure.ac 无测试宏 | 「grep -nE 'AC_CONFIG_TESTDIR\|_TESTS\|CTEST\|tests' configure.ac」 | 无匹配，**rc=1** |
| meson.build 无 test() 调用 | 「grep -nE '^[[:space:]]*test[[:space:]]*\(' meson.build」 | 无匹配，**rc=1** |

⇒ 结论：上游 xev 1.2.7 **无自动化测试套件**（N_static=0、N_registered=0），
与 harness 自证的「HMBS_UPSTREAM_TEST_RESULT」一致（见下真机日志原文，discovered:0）。

## 五维测试数字账本

| 维度 | 值 | 依据（同源） |
|---|---|---|
| N_static（上游源码静态计数，行首锚定） | **0** | 上表「grep -cE '^[[:space:]]*assert…' xev.c」=0；无 tests/ 目录；无 *_test.c |
| N_registered（ctest/meson/TESTS 注册数） | **0** | Makefile.am「grep TESTS\|check」rc=1；Makefile.in 无 TESTS=；meson.build 无 test()；configure.ac 无测试宏；harness「HMBS_UPSTREAM_TEST_RESULT…discovered:0」 |
| N_executed（真机实测，通过/失败/跳过/disabled 分列） | **4**：通过 4 / 失败 0 / 跳过 0 / disabled 0 | w3-local-ci.log 第 436 行 RUN 命令 + 第 443/446/468/490 行四条 PASS + 第 491 行「OK: all 4 checks passed」+ 第 492 行「passedCount:4」 |
| 未执行分类与原因 | ① L2 smoke（version/help）= **skip**；② GUI 事件循环（XNextEvent/do_RRNotify_*/绘制）= **未覆盖** | ①原因见「L2=skip 实测取证」——裸跑缺 conan 运行期库路径（本轮冷验后复测数字不变：裸跑 127 / 注入库路径 0）；②原因需真实 X server + 交互，无头不可执行 |
| N_consumer（消费者程序数，N_assertion 括注） | **1** 程序（test_xev.sh），N_assertion = **4** | test_package 运行命令 = w3 log 第 436 行；自证行 = 第 491 行「OK: all 4 checks passed」/第 492 行「passedCount:4」 |

声明数 ≤ 实测数：PR 正文声明 executed=4（=N_assertion）。
（注：以下 w3-local-ci.log 行号对应**本轮冷验后**的 .ci-result
（integrity_hash「f08ae7bf497cb201」，log_sha256「1b9127acbf8bccd5e3c9df9f2508c158d21ca8bebd3aaca570cc1293da203253」，
共 523 行）所绑定的报告版本，已逐条用「sed -n 'Np'」复算；逐字文本仍是稳定定位依据。）

## L2=skip 实测取证（如实保留，不改判不删分母）
harness 的 L2 smoke 判据（「ci/conan/build_and_test.sh」1676–1706 行）是对包内可执行文件
**裸跑**「timeout 15 "$bin" --version </dev/null >/dev/null 2>&1」，**不注入 conan 运行期库环境**。
本机复现（本轮冷验产出的包内二进制
「~/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev」，43456 字节，2026-09-24 03:27）：

- 裸跑「--version」/「--help」退出码 = **127**（加载期即失败），首条真实报错逐字：
  「Error loading shared library libXrandr.so.2: (needed by /storage/Users/currentUser/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev)」，
  并伴随「Error relocating …/p/bin/xev: XOpenDisplay: symbol not found」等一整套 DT_NEEDED 未解析符号
  （libXrandr/libX11/libXrender/libXext/libX11-xcb/libxcb 全家桶/libXau/libXdmcp 全缺，共 31 条
  Error loading + 34 条 Error relocating）。
- **逐字复刻 harness 判据**（「env -i timeout 15 "$BIN" --version </dev/null >/dev/null 2>&1」）
  退出码同样 = **127**（记录名「harness_version_rc=127」）。
- 同二进制**注入 conan 依赖库路径后**（LD_LIBRARY_PATH 取自本轮新日志第 436 行 test_package RUN
  命令行里的各依赖 p/lib，共 7 个目录）：
  「xev --version」输出「xev 1.2.7」、退出码 = **0**；「xev -version」同样「xev 1.2.7」/**0**。

⇒ L2=skip 的真实成因 = **裸跑 smoke 探针未带 conan 运行期库路径，动态加载器在进 main 之前就
解析不到 libXrandr.so.2 等 DT_NEEDED（exit 127，XOpenDisplay symbol not found），与 -version/--help
逻辑本身能否早于 XOpenDisplay 退出无关**。这不是包缺陷：一旦提供运行期库寻址路径，四条命令行路径
全部正常（test_package=L1 已注入 LD_PRELOAD，故 4/4 通过）。
⇒ 本轮强制冷验后该结论**不变**（127 与 0 两个数字都是在冷验重建的新二进制上重测的）。

⚠ 说明：任务下发口径推测的 skip 原因是「version/help 未能打开 display 之前退出」，但**实测证据不支持**
该说法——失败发生在加载期（symbol not found），根本没到 option 解析与 XOpenDisplay 调用；已按实测改写。
同族先例「archives/x/xbanish/1.8」是「L2=skip（本包无 version/help 且需 X）」；**该借例路径不在
主干与本 PR 基线内**（实测本 worktree：「git ls-files archives/x/xbanish」无输出；它只存在于未合入
分支「origin/feat/xbanish-1.8」，审查员在主树按图索骥会落空，故引用须带此分支限定）。xev 不同：确有
-version/-help 且源码层面确早于 XOpenDisplay（xev.c 第 1352/1363 vs 1384），只是本机裸跑缺库路径。
两例都如实保留 skip、未写成通过（该先例的「max_rss_mb: 83」同样只在该未合入分支内，见下节口径）。

## 验证结果

### conan-verify（G0–G4，home-B-xev，profile ohos-aarch64 via 文件路径）
```
G1 配方完整性: PASS    G0 预构建风险: PASS
G2 conan create（含 test_package 真机执行）: PASS
G3 系统同名库隔离(R26): PASS    G4 产物完整性: PASS    CONAN_VERIFY_RC=0
```
本轮换 conandata 后重跑过两次：一次在改配方之后、清缓存之前（该次 G2 冷取源码并打印
「Sources correctly downloaded from …/xorg.freedesktop.org/pub/…」，见上节），
一次由 finish 内部再跑（同样全绿）。W3 的取源证据以「Calling source 命中 1 次」为准。

### 真机 w3-local-ci.log 关键段（逐字，行号为**本轮冷验后**该日志内行号，共 523 行）
```
99:  found 2 source URL(s)
100: [try 1/1.1/3] xev-1.2.7.tar.gz ← https://xorg.freedesktop.org/pub/individual/app/xev-1.2.7.tar.gz...
101: [ok] xev-1.2.7.tar.gz (176KB) via mirror 1
102: [cached] xev-1.2.7.tar.gz (0KB)
207: xev/1.2.7: Calling source() in /storage/Users/currentUser/tmp/ch/home-B-xev/p/xev5c6205c0ea6f0/s
208: xev/1.2.7: Sources correctly downloaded from .../predl_cache/2e2a1c23_xev-1.2.7.tar.gz（180306B 真包）
436: xev/1.2.7 (test package): RUN: "/bin/sh" ".../test_package/test_xev.sh" ".../p/b/xevc2ac95246249e/p/bin/xev" ".../libXau…:...:…/libXrandr.so.2.2.0"
441: [test 1/4] xev -version
443: PASS: xev -version reports 'xev 1.2.7' (exit 0)
444: [test 2/4] xev --version
446: PASS: xev --version reports 'xev 1.2.7' (exit 0)
447: [test 3/4] xev -help
468: PASS: xev -help prints usage banner (exit 0)
469: [test 4/4] xev -Zz (unrecognized option -> nonzero exit)
490: PASS: xev -Zz rejected with usage + nonzero exit (rc=1)
491: OK: all 4 checks passed
492: HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xev.sh","discovered":4,"passedCount":4}
494: HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make -n check (no check target)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xev 1.2.7 上游无测试套件：Makefile.am 无 check/TESTS 目标、meson.build 无 test()、源码树无 tests/ 目录、xev.c 无 assert()"}
495: [ok] xev/1.2.7 — conan create passed
497: [ok] L1a: test_package was executed by conan create
502: [ok] L5: bin/ has content
503: [step] L1e: Destructive negative test (R34)...
505: [ok] L1e: Negative test confirmed — test genuinely depends on xev
509: L0_RESULT=pass: all checks passed
510: L1_RESULT=pass: upstream tests + test_package executed
511: L2_RESULT=skip: xev version/help failed
512: L4_RESULT=pass: patches clean
513: L5_RESULT=pass: bin/ has content
521: Pass rate: 100.0% (1/1)
522: [step] All packages built and tested successfully ✅
```
（第 101 行「via mirror 1」是框架重试循环的**序号标签**——pub/ 不命中镜像正则，候选列表只含官方
URL 本身，序号 1 即官方源；第 102 行 0KB 那条是第二条 archive/ 命中上一轮残留的 162 字节 404 页，
正是「必须把 pub/ 排第一」的现场。为避免交付树内出现本地路径型 URL 字面量，预下载收尾行（第 103 行）
不逐字抄，按行号定位。）
（注：上游「make -n check」在解出的源码树因无已配置 Makefile 返回「No rule to make target 'check'.」；
harness 在真正构建目录执行并记为 discovered:0，与上表静态取证一致。）

### 关键适配点（含失败方案）
1. **失败方案 A（已废弃）**：把依赖 include/lib 用 shlex.quote 整串作为 configure 命令行
   「XEV_CFLAGS='<...>'」注入 → autoconf 把字面单引号存进 Makefile
   （「XEV_CFLAGS = '-I/a -I/b'」），make→/bin/sh 将整串塌成**单个**畸形 -I token，
   所有头文件路径失效 →「fatal error: 'X11/Xlocale.h' file not found」（首个真实错误）。
   **最终方案**：改用 conan 规范 AutotoolsDeps 生成器注入依赖 -I/-L/-l，
   「PKG_CHECK_MODULES(XEV,…)」走真实 pkg-config（PKG_CONFIG_PATH 含各依赖
   lib/pkgconfig 与 share/pkgconfig，后者是 xorgproto 协议 .pc 所在）→ G2 PASS。
2. **失败方案 B（已废弃）**：「tc.extra_env.define("PKG_CONFIG_PATH", …)」→
   conan 2.29.1 AutotoolsToolchain **无 extra_env 属性**（AttributeError）。
   **最终方案**：PKG_CONFIG_PATH 作为 configure 命令行参数传入（xeyes 同款）。
3. Xlocale.h 由 conan libx11/6.4.0 包「include/X11/Xlocale.h」提供，非 xorgproto；
   故必须让 libx11 的 include 真正进入编译命令行（方案 1 修复后即命中）。
4. **依赖 .pc 目录的注入方式（如实到代码行）**：本配方**未使用 PkgConfigDeps 生成器**
   （conanfile.py:36 的 import 只有 Autotools、AutotoolsToolchain、AutotoolsDeps），
   也**未声明 util-macros**（requirements() 见 conanfile.py:58-64，只有 libx11/libxrandr/libxcb/libxau）。
   真实做法是：_pkg_config_dirs()（conanfile.py:72-86）遍历全部 host 依赖的 lib/pkgconfig 与
   share/pkgconfig 两个目录，拼成路径串后**作为 configure 命令行变量**追加
   （conanfile.py:106，且 conanfile.py:100-103 会保留进程原有的 PKG_CONFIG_PATH 值），
   依赖的 -I/-L/-l 则由 AutotoolsDeps 生成器注入（conanfile.py:108-109）。
   真机 configure 命令行逐字可见该变量（w3-local-ci.log:223，该行的 PKG_CONFIG_PATH 段共 9 个
   pkgconfig 目录＝7 个 lib/pkgconfig ＋ 2 个 share/pkgconfig，用「sed -n 223p … | grep -o pkgconfig | wc -l」
   复算），无任何 PkgConfigDeps 生成物。
   与既有条目 E468 的关系＝**部分同源**：本包撞上的是「依赖的 .pc 目录不会自动出现在
   PKG_CONFIG_PATH 里、须自行注入」这一半；E468 的另两半在本包**均未发生**——既没有 PkgConfigDeps
   可谈，util-macros 也未声明；真机上 configure 对 xorg-macros 的 pkg-config 查询确实未命中
   （w3-local-ci.log:312-315），但紧接「checking for XEV... yes」（:316）、configure 正常进入
   config.status 生成阶段（:318）⇒ 对本包不阻塞，本包不据 util-macros 主张任何经验。
   （下方 B 判定段对 E468 的口径已同步收窄。）
5. **构建期对上游 configure 的就地改写（等价于补丁，但以代码形式存在）**：
   _rewrite_configure()（conanfile.py:135-162）在解出的源码树内把 configure 的 umask 077 改为
   umask 022，并给 ac_pwd 的 pwd 判定加 PWD 环境变量回退后写回文件；_prepend_toolchain_path()
   （conanfile.py:111-133）改写进程 PATH；build()（conanfile.py:164-173）另有 os.chdir 到
   build_folder 并预置 PWD。
   必要性：HMDFS 上 conan 缓存父目录 getcwd() 不可达（configure 顶部 pwd 判定会报 working
   directory cannot be determined）；CI worker 的 PATH 缺工具链目录（clang 绝对路径可用，但其内部
   ld.lld/as/nm 走 PATH 解析，否则 configure 报 C compiler cannot create executables）。
   先例＝配方自身注释里点名的同款处理（xeyes/nspr/libgsf 见 conanfile.py:136；xeyes/flint 见
   conanfile.py:112）。
   ⇒ 交付物的 patches/ 目录为空＝**没有补丁文件**，但**不等于零源码改动**。

## 资源占用（max_rss）
memcap 探针实测值：「MEMCAP[probe] peak=205MB budget=0MB rc=1 用时292.1s」，出处
「~/tmp/uc2/xev-diag/06-finish-20260924-022954.txt.prev-20260924-0300」第 164 行
（该行于本轮开工后再次用「sed -n '164p'」复算，逐字一致；该文件是上一时间点对**同一份 conanfile.py**
套「memcap-run.py --probe」跑 finish 的记录）。本轮冷验按既定口径用
「gate.sh + build-slot.sh --kind short」直跑 finish，未再套 memcap 包装器，故此处只保留
上述可溯源的实测值、不新造数字。**主干已合入的归档里没有任何文件含 max_rss_mb 字面量**
（可复算命令：「git grep -l max_rss_mb origin/main -- archives」⇒ 无命中、rc=1，本轮在 B 机
worktree 实跑）。xev 的 manifest.yaml 遵此不设该字段，避免写入非实测/占位 0 值。
（口径说明，防自指误读：在本 worktree 工作树里跑「grep -rl max_rss_mb archives/」**会**命中
两个文件——本包的 notes.md 与 reports/test-report.md，即写下这句话自己的那两份说明文字；
命中的都不是 manifest.yaml，也不涉及别的包。绝对化结论只对**主干 origin/main** 成立；
未合入分支「origin/feat/xbanish-1.8」的 archives/x/xbanish/1.8/manifest.yaml 第 73 行就写有
max_rss_mb: 83，属该分支私有内容，不在上述口径内。）探针实测评估值 205MB 记录于此备查。

## B 判定（定性，写死不改判）
**B判定=hit**，命中既有条目，不升 create、不建 Issue：
- **E299**（「knowledge/doc/E299.md」，signature 字面含「sha256 hash failed for」与「404 Not Found」；
  rec=classify-source-failure：按传输/HTTP 状态/完整性分层诊断，始终保留官方源或权威镜像）。
  本次 W3 投喂 404 页导致「sha256 hash failed」的取证与修法正是该方法的落地，且本轮把分层做全：
  传输层（www.x.org TLS 主机名不匹配 ⇒ rc=60）→ HTTP 层（框架只看 size>100B、不看状态码）→
  完整性层（conan 逐条校验 sha256，故首条必须是能取到真包的官方 URL）。修法是**换官方主机内可达的
  路径段排序**，**不改哈希、不加第三方前缀**。
- **E468**（**部分同源命中，口径已按 HEAD 代码收窄**）：该条目的两半机制是「PkgConfigDeps 只写
  .pc 不入 PKG_CONFIG_PATH」与「X.Org 另需 util-macros 提供 xorg-macros.pc」。**本包两半都不成立**：
  配方未 import/使用 PkgConfigDeps（conanfile.py:36），也未声明 util-macros（conanfile.py:58-64）。
  本包真正撞上并沿用的是它的同一半问题——依赖的 .pc 目录不会自动进入 PKG_CONFIG_PATH，须由配方
  自行收集（conanfile.py:72-86）并以 configure 命令行参数注入（conanfile.py:106；真机命令行
  w3-local-ci.log:223），对应上文关键适配点 1/2/4。xorg-macros 那条查询在本包未命中且不阻塞
  （w3-local-ci.log:312-315，紧接 :316 checking for XEV... yes）。⇒ 本包对 E468 的命中**仅限
  pkgconfig 路径需自行注入**这一点，不主张 util-macros/PkgConfigDeps 相关经验，也不据此升 create。

框架侧缺陷（W3 预下载不校验 HTTP 状态码与 sha256 / conan_verify.py 无条件改写 GitHub URL）
**不在本包修**，仅在此点名，属单独 PR 范畴。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方，conan 依赖 libx11+libxrandr，AutotoolsDeps 注入 -I/-L/-l，package() 自签 bin/xev |
| conandata.yml | 同一官方主机的两条官方路径（pub/ 在前、archive/ 兜底）+ 实测 sha256（**未改哈希**、无第三方代理前缀、无本地路径型 URL、注释内不带协议 URL 串） |
| test_package/conanfile.py + test_xev.sh | 无头真跑 4 条命令行断言 + LD_PRELOAD 运行期兜底 |
| test_package/MANIFEST.yml | 上游无测试审计（upstream_tests_exist:false）+ assertion_count=4 |
| manifest.yaml | 版本级归档信息（无 patch_generation/patch_classification 污染块，无 max_rss_mb 字段） |
| reports/test-report.md | 五维账本与同源实测证据 |
| commands.json | 软件级命令声明（R38，type=tool）。versions.1.2.7 的 binary=**true**，口径在此写死以免与姊妹包口径打架：该字段表示**本版本在真机构建出、并被 harness 的 L5 产物门禁校验过的可执行文件是否存在**。本包为真：package_type=application（conanfile.py:49）、cpp_info.bindirs 只暴露 bin/（conanfile.py:199-204）、make install（w3-local-ci.log:342）、llvm-objcopy 去 .codesign 与 binary-sign-tool 自签（:360、:362）、[ok] L5: bin/ has content（:502）与 L5_RESULT=pass（:513）；实体包内文件「~/tmp/ch/home-B-xev/p/b/xevc2ac95246249e/p/bin/xev」实测 43456 字节、mtime 2026-09-24 03:27:51、file(1) 逐字判读为「ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped」、sha256 23941ea4a80a74e1d23240d15bffcef65a2d6d92c383251412e020e26f4ea28b。口径背景：仓内该字段此前 true/false 混用且无权威定义——实测本 worktree 的「archives/x/*/commands.json」里 binary 条目**本笔改动前**为 false 20 / true 10（含本包原那条 false），**改动后**为 false 19 / true 11；type=tool 的同族先例「archives/x/xeyes/commands.json」（xeyes 1.3.1）为 true。复算命令：「grep -rh binary: archives/x/*/commands.json | sort | uniq -c」 |
| patches/ | 空（**无补丁文件**；conandata.yml:26 patches 为空、manifest.yaml:37 patches_applied 为空，本轮复算三处自洽）。≠ 零源码改动：构建期对上游 configure 的等价就地改写见 conanfile.py:135-162（_rewrite_configure）与 :111-133（_prepend_toolchain_path），逐条说明见上文关键适配点 5 |
---

**编译结束**: 2026-09-24 03:27
**最终状态**: built


## 附：上游测试语义澄清（2026-09-25 CIW-1，回应审查意见）

- 本包上游**无测试套件**：`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","discovered":0,"executed":0}`（reports/w3-local-ci.log 第 494 行自证）；正文「上游测试用例统计」如实声明 0 用例。
- 门禁 `L1_RESULT=pass: upstream tests + test_package executed` 中的 `pass` 属**空真判定**语义：上游 `Makefile.am` 无 `TESTS`/`check_PROGRAMS` ⇒ L1c 无套件可跑、该项按空真放行，**不构成「上游测试已执行」的主张**。
- 真实测试证据 = 消费者侧 test_package：`test_xev.sh` 4 用例实跑实断全过（见「适配后测试用例统计」）。
- 按「勿直接改写已留存日志」要求，原始 `w3-local-ci.log` 未做任何改写；本段为说明性补充。
