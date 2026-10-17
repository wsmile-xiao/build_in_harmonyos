# radvd 2.20 适配笔记

## 编译环境
- 构建系统: autotools（上游 release 包自带预生成 configure / Makefile.in / config.h.in）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（profile ohos-aarch64，os=OHOS / arch=armv8 / os.version=6.0）
- 构建主机: B 机（HarmonyOS aarch64，8 核 / 31G）
- 状态: built（conan create 通过，未上传制品仓）

## 编译步骤（配方内实际形态）

```bash
python3 scripts/ohc-run.py conan-verify radvd 2.20
# 判决口径（与 PR 正文「未执行与未覆盖的检查（诚实披露）」同一口径，不写「全绿」）：
#   G0/G1/G2/G3 = PASS；
#   G4 = 报告打 `✅ PASS`，下一行 `⚠️ 无法找到程序包 ID` ⇒ 未取得制品包 ID，属未真正核对的 PASS；
#   L2/L4/L5 = 报告打 `✅ PASS`，下一行 `⏭️ 跳过（无 cache 路径）` ⇒ verify 侧未执行；
#   G4 与 L2/L4/L5 的真实执行性由本地 W3 的 `L5`+`L1e` 与消费者断言补偿，不当作已通过。
#   报告原文见 reports/conan-verify-report.md L39-49；逐项披露见 reports/pr-body.md「未执行与未覆盖的检查」。
python3 scripts/ohc-run.py finish radvd 2.20 built     # 内含 W3 本地 CI 模拟
# 等价手工步骤：
./configure --prefix=<build_folder>/prefix --with-check
make -j1 && make check -j1 && make install -j1
```

`--with-check` 是唯一的非默认 configure 参数：上游 Makefile.am 的 `check:` 目标在
`with_check=no` 时直接 `$(error libcheck not available)`，不带它就跑不了官方测试。
bison/flex 是 tool_requires —— 官方包**不**含预生成的 `gram.c` / `lex.yy.c`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 起手 `cannot guess build type; you must specify one` | config.guess（timestamp 2018-02-24）不识别 `uname -s`=HarmonyOS | 补丁 0001 加 HarmonyOS 分支输出 `aarch64-unknown-linux-ohos`；本版 config.guess 的 case 风格是 `echo ...; exit ;;`（不是新版的 `GUESS=` 变量），照抄新版写法会命中分支却不输出 |
| 2 | `Invalid configuration aarch64-unknown-linux-ohos: system ohos not recognized` | config.sub（2018-02-22）两处 OS 白名单不含 ohos | 补丁 0002 补 `linux-ohos*` / `-linux-ohos*`；三元组含 linux ⇒ 上游 configure.ac 的 `case "$target" in *linux*` 归入 linux 分支并定义 `_GNU_SOURCE`（musl 下暴露 `in6_pktinfo` 必需） |
| 3 | `config.status` 报 `error: could not setup config files machinery` | HMDFS 上 config.status 以 `umask 077` 建的 `./confXXXXXX` 不可写，写 subs1.awk 报 Permission denied（知识条目 E011/E052/E112/E114/E129 家族，zile 2.6.4 补丁 0002 同法） | 补丁 0003 把两处 `umask 077` 改 `022` |
| 4 | 第一个 .c 即 `fatal error: bsd/string.h: No such file` | includes.h 在 `!__FreeBSD__` 下无条件 `#include <bsd/string.h>` 兜底 strlcpy；目标平台全盘无该头 | 补丁 0004 改成需显式 `-DUSE_LIBBSD_STRLCPY` 才走 libbsd。依据：`nm -D libc.so` 有 `T strlcpy`、sysroot `<string.h>` 有声明、只链 libc 的探针程序编译+运行通过、configure 的 `AC_SEARCH_LIBS(strlcpy, bsd)` 自己报 `none required` ⇒ 不新增依赖 |
| 5 | `make check` 起手 `error: ../config.h file not found` | test/print_safe_buffer.{c,h} 用 `#include "../config.h"`；Conan VPATH 外树构建下 config.h 在构建树、相对路径按包含者目录解析到源码根 | 补丁 0005 改成 `#include "config.h"`，由 -I/-I$(srcdir) 兜住；同目录 test/check.c 本来就是该写法，这里只是对齐两个漏网文件 |
| 6 | `make check` 只跑到 17/36 并报 3 处 failure | 上游 test/util.c、test/send.c 用字面量 `test/test1.conf` 读配置，automake 的 TESTS 以**构建树**为 cwd，外树构建时数据文件只在 source_folder/test/ 下 ⇒ readin_config() 返回 NULL 并连带中断后续用例 | 在 build() 里用 `files.copy("*.conf", source_folder/test → build_folder/test)` stage 测试数据，不改上游路径写法。实测 36/36 全绿 |
| 7 | G2 报 `Error in source() method, line 81`（无任何编译器错误行） | 取源面：conandata 里残留 `ghfast.top` 镜像前缀，该域名在 B 机连接超时（`ConnectTimeout ... connect timeout=30` ×2）。机制见下文「本地 W3 的 conandata 污染」 | 还原为官方单值 URL、sha256 一字未动（commit `42d8b5a23`）。取源靠 `core.sources:download_cache=~/tmp/ch/dlcache` 命中；缓存内 tarball 的 sha256 实测与 conandata 声明值完全相同（`af37c5a8...4220`） |

## 本地 W3 的 conandata 污染（框架机制，务必知道）

`ci/conan/build_and_test.sh` 的 Mirror fallback 段（匹配式 L1153、改写执行 L1154、回写 L1156-1157）会把 conandata.yml 的单值 `url: "https://..."`
改写成含镜像前缀的**列表**（`get_mirrors()` 对 GitHub 源产出 `https://gh-proxy.com/<url>` + 官方），
而 L1179 的 `PREDL_BACKUP=cp conandata.yml` 发生在该改写**之后** ⇒ 结尾的
`_restore_conandata()` 只能还原到「已注入镜像」的形态。后果：每跑一次本地 W3，
conandata.yml 都会被留在带 `gh-proxy.com` 的状态，随手 commit 就是把镜像域名写进提交态
（PF7 源URL闸 / R39 都把它列黑名单；上一轮 `fc7a4a863` 正是这样把 `ghfast.top` 提交进去的）。
本窗处置：W3 跑完用 `git show HEAD:archives/r/radvd/2.20/conandata.yml > 同路径` 还原，
并在本窗落盘工具里加了 `ghfast.top|gh-proxy.com` 残留自查（`~/tmp/uc2/z34-radvd/ck34.sh`）。
框架文件本身未改（属 ci/ 红线）。

## netlink 与运行时能力面（实测）

- `config.h:35` 为 `/* #undef HAVE_NETLINK */`；`config.log:170-173` 显示探测在
  OHOS musl sysroot 上因 `<sys/socket.h>` 与 `<linux/netlink.h>` 同含导致 `sockaddr_storage`
  重定义而失败。这是上游 configure.ac 自身的降级分支（`AC_MSG_RESULT(no)`，非硬错误），
  radvd 因此走 ioctl/getifaddrs 路径取接口信息 —— **未加平台宏强行打开 HAVE_NETLINK**（R8/PF5）。
- 设备能力面（`open()` 系探针 + 真跑，见 reports/runtime-*.out）：
  `AF_NETLINK/NETLINK_ROUTE` 可用、IPv6 地址存在、`IPV6_JOIN_GROUP` 可用，
  但 `AF_INET6/SOCK_RAW/IPPROTO_ICMPV6` = **EPERM**（无 CAP_NET_RAW）⇒
  RA 发送与 radvdump 抓包属**权限面**，不是内核缺陷也不是配方缺陷。

## 验证结果

```bash
$ radvd -c -C ra-test.conf -m stderr       # 配置校验（-c/--configtest）
$ echo $?                                  # 0
$ radvd -n -C ra-test.conf -m stderr       # 真实启动，走到打开 RA 套接字
[Sep 25 01:22:53] radvd (2858): version 2.20 started
[Sep 25 01:22:53] radvd (2858): can't create socket(AF_INET6): Permission denied
open_icmpv6_socket: Permission denied      # RC=1，权限面
$ radvdump -d lo                           # 抓包，同一处 EPERM
[Sep 25 01:23:43] radvdump (3920): can't create socket(AF_INET6): Permission denied
open_icmpv6_socket: Permission denied
```

（上面四行与本机留档 `reports/runtime-radvd-ra.out`、`reports/runtime-radvdump.out` 逐字同源。）

上游 usage 实测：`-c, --configtest  Parse the config file and exit` /
`-t, --chrootdir=PATH  Chroot to the specified path` ⇒ 配置校验的正确开关是 `-c`
（配 `-C` 指定文件），`-t` 是 chroot，与 test_package/test.sh 的注释一致。

## 依赖版本

| 依赖 | 版本 | 形态 | 制品仓 |
|---|---|---|---|
| bison | 3.8.2 | tool_requires | 已发布（W3 的 L0i 逐项核实） |
| flex | 2.6.4 | tool_requires | 已发布 |
| check | 0.15.2 | test_requires | 已发布 |
| 运行时 | 仅 libc / libc++ | 无 conan 依赖 | — |

## 交付物

产物为两个可执行文件（`sbin_PROGRAMS` ⇒ Conan 归一到 `${prefix}/bin`）：
`radvd`（117120 B）与 `radvdump`（39296 B），另有 `radvd.conf.example` 与 man 页、
`licenses/COPYRIGHT`、`licenses/CHANGES`。纯 application 包，无 .so/.a ⇒ R26 不涉及
系统同名库冲突（G3 PASS）。R38 的 `commands.json` 已在软件级目录声明。

## 注意事项

- 本包**不含** `packaging/`：取数基线 `origin/main = 48d9cee6844d0fca1f25e86c2df1293b904855d8`（2026-09-25 实测），
  `archives/<字母>/<包>/<版本>` 层共 **7750** 个版本目录，其中带 `packaging/` 子目录的仅 **75** 个（**0.97%**）；
  `.staging-verified` 仅 **2** 个（`archives/c/cloog/0.21.1`、`archives/k/kics/2.1.20`）
  ⇒ 属历史遗留形态，`submit` 的 4 道 Gate 也不查它，不造。
  **复现命令**（在仓根跑，两条即得上面两个数）：
  ```bash
  S=48d9cee6844d0fca1f25e86c2df1293b904855d8
  git ls-tree -r -d --name-only $S -- archives | awk -F/ 'NF==4' | wc -l                      # 7750
  git ls-tree -r -d --name-only $S -- archives | awk -F/ 'NF==5 && $5=="packaging"' | wc -l    # 75
  ```
  两个口径陷阱：①**别用裸 `grep '/packaging'`** —— 仓内有一个**名为 `packaging` 的 Python 包**
  （`archives/p/packaging/26.3`），且 `archives/f/freac/1.1.7/packaging/` 下还有数十枚嵌套子目录，
  实测 `grep -c '/packaging'` = 126、按 `NF>=5` 去重 = 77，都会把 75 抬高；
  ②命令里**钉 sha 而不是写 `origin/main`** —— 该 ref 在取数期间会被上游合入推进，数字会漂。
- CI 取源风险需在 PR 正文预声明：官方 GitHub URL 在 B 机直连 25s 超时，本地只能靠
  dlcache/predl；CI 侧的镜像改写存在「拿到 162B 的 404 HTML 且不校验状态码 ⇒ sha256 必败」
  的已知家族（E299，先例 pfstools #12432 已在正文预声明）。

## 路径 B 声明（与 knowledge/drafts 同 stem 成对件同源）

- **适配路径**：路径 A+B —— A 为 radvd/2.20 的基础适配（5 枚 OHOS 移植补丁 + 配方 + 消费者测试），
  B 为新增一条**跨库可复用**的构建门禁副作用机制（本地 W3 的 conandata 还原为何必然不彻底）。
- **使用知识库**：hit(E011 处方 edit-umask-in-configure —— 同签名 `could not setup config files
  machinery` + `subs1.awk: Permission denied`，本包补丁 0003 改 configure 内 umask 即该条已登记解法)、
  hit(E415 —— 同症状「跑完 CI/W3 后 conandata.yml 必脏」，其处方「事后核验并恢复与 HEAD 逐字节一致」
  本包照做，本条知识正是对它的新增价值所在)、
  hit(E287 —— 鸿蒙无 CAP_NET_RAW、raw socket 打开即失败属既有的**权限面认定**，本包
  `can't create socket(AF_INET6): Permission denied` 落在同一认定内；该条的 corpus runner 解法本包不适用)、
  参考(E237 的「仅编译验证 + 不虚构可运行结论」处置口径用于本包两项未执行运行时的申报方式，
  **不同签名故不计 hit**，只作口径依据)。
  **不成立的既有倾向条目** —— 登记表原写「strlcpy 属既有家族」不成立，
  本仓 `knowledge/doc/`、`knowledge/graph/` 全盘 `grep -rln strlcpy` **零命中**，
  只有 `knowledge/drafts/DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge` 一枚草稿，
  而它的前提是「musl/OHOS **缺** strlcat/strlcpy」，与本包实测相反（`nm -D libc.so` 有 `T strlcpy`、
  sysroot `<string.h>` 有声明、configure 的 `AC_SEARCH_LIBS(strlcpy, bsd)` 自报 `none required`）；
  本包补丁 0004 的实际障碍是上游 `includes.h` 无条件 `#include <bsd/string.h>` 兜底，属另一签名。
  按「一 PR 一知识」该机制**不进本 PR**，另行投 `经验文档/B草稿库/` 通用池。
- **知识库扩展**：create —— `knowledge/drafts/DRAFT-radvd-2.20-conandata-predl-backup-after-mirror-rewrite.md`
  与同名 `.kv` 成对。一句话机制 —— `build_and_test.sh` **先**把 conandata.yml 的单值 url 改写成镜像列表
  （L1154，改写后第 4 行即为 `https://gh-proxy.com/...` 项），**之后**才做预下载备份
  （L1179-1180 `PREDL_BACKUP`），于是 L1188 注册的 `trap _restore_conandata EXIT` 只能撤销 L1293 的
  `file://` 替换、撤销不了镜像注入 ⇒ 每跑一次本地 W3，conandata.yml 提交态必脏；
  收口建 PR 前必须**单独**从 HEAD 还原这一枚文件并把禁词计数做到 0（`pipeline run` 第 [4/8] 步按目录
  形态 `git add`，不会替你挑出来）。真实落地证据 —— 本分支 `fc7a4a8637` 把镜像前缀写进过提交态，
  `42d8b5a231fac17628078bbc75c08b7b064488e1` 才还原（sha256 一字未动）。
- **关联 Issue**：#3350 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3350

## 对话记录

### 对话 #1 [2026-09-25]
问题: G2 报 Error in source() 但无编译器错误行，交接件疑为 ghfast 镜像失效。
操作: 复跑 conan-verify 只看取源段；比对 conandata 三个版本（HEAD/工作区/.orig）与 predl 缓存 tarball 的 sha256；读 build_and_test.sh L1149-1153 与 L1179 的改写-备份顺序。
结果: 定性为取源面 - 提交态被工具注入的 ghfast.top 前缀（已随 17:15 那次落盘被 commit）。还原官方单值 URL（commit 42d8b5a23，sha256 未动）后 G2 PASS，finish Step2 的真实阻塞项暴露为 manifest.yaml/notes.md 缺失（close_archive.py:28-31）。
---

**编译结束**: 2026-09-25 01:36
**最终状态**: built
