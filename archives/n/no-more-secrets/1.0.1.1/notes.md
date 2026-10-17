# no-more-secrets 1.0.1.1 — 适配笔记

## 软件信息
- 上游: https://github.com/bartobri/no-more-secrets（官方 tag `v1.0.1`）
- 语言: C（GPL-3.0-or-later）
- 构建系统: 纯 GNU Make（无 configure）
- 产物: `nms`、`sneakers` 两个命令行工具 + man 页（man6）

## R37 版本递增：1.0.1 → 1.0.1.1 的四处修复

制品仓已存在 `no-more-secrets/1.0.1`（制品仓直查 HTTP 200），本次交付递增为
`1.0.1.1`，修掉 1.0.1 的三处遗留问题 + 一处完整性缺失：

1. **运行期 terminfo 缺口（核心修复）**：`nms` 走 ncurses 特效路径，`initscr()`
   需要 terminfo 数据库；OHOS `/usr/share/terminfo` 不完整，1.0.1 未随包分发
   terminfo，程序在真机上只被验证到 `nms -v`（该路径在 ncurses 初始化之前
   直接返回），特效路径是否可运行无人验证过。→ 按知识库条目
   **terminfo-database-bundle**（E5xx）规范：`package()` 从 ncurses 依赖复制
   `share/terminfo`，`package_info()` 定义 `TERMINFO`/`TERMINFO_DIRS`
   （`ne 3.3.4`、`boxes 2.3.1`、`astroterm 1.0.9` 同款）。
2. **依赖换为 OHOS 适配版 ncurses/6.4**：6.4 是本仓适配配方（OHOS 补丁
   `0001-port-for-ohos.patch`，`--without-shared` 静态专用，`_validate_package()`
   强制校验 `share/terminfo` 存在），满足 **R4/R26**（终端工具静态链接方可
   部署）；6.6 无该保障。
3. **消费者测试形同虚设**：1.0.1 的 test 只做 `nms -v` + `sneakers` 存在性
   （assertion_count: 2），**在一个 nms 根本无法运行的环境里也会全绿**。→
   1.0.1.1 改为 pty harness（知识库条目 **tui-app-pty-test-harness** E5xx
   同族做法）：两个工具都在伪终端下端到端跑真实功能，含负向注入控制。
4. **补全软件级 `archives/n/no-more-secrets/manifest.yaml`**（1.0.1 只有版本级
   manifest；同期合入的 abuild/unlzx 等均有软件级清单与多版本索引）。
5. 附带：补丁最小化（仅两条链接行）、源码 URL 加成镜像列表（见下）。

## 适配决策
1. **选 ncurses 实现**：上游提供无依赖的 ANSI/VT100 版（`make nms`）与
   ncurses 版（`make all-ncurses`，链接 `-lncursesw`）。主流发行版打包
   均采用 ncurses 版，终端兼容性更好；本配方以 Conan 依赖方式引用
   OHOS 适配版 `ncurses/6.4`（静态 `libncursesw.a`，头文件位于 include/ 根，
   `<ncurses.h>` 直接可用）。
2. **patch 0001-Makefile.patch（最小化重写）**：上游 `-ncurses` 链接目标只有
   `$(CC) $(CFLAGS)`，无法传入 `-L<依赖libdir>`（交叉工具链必需）。
   补丁仅在 `nms-ncurses`/`sneakers-ncurses` 两条链接行加入 `$(LDFLAGS)`，
   共 1 个 hunk / 2 行改动（1.0.1 的补丁还夹带了一处尾随空白清理，已剔除）。
   通用构建增强，不含平台宏（`type: portability, platform_only: false`，
   与 zerofree 1.1.1 的 0001 同因同型）。
3. **in-source 构建**：上游 Makefile 无 VPATH，无法 out-of-source；
   配方 layout 设 `folders.source = folders.build = "."`。
4. **不走 `make install`**：OHOS 构建沙箱缺少可用的 GNU coreutils
   `install`；package() 直接 conan copy `bin/nms`、`bin/sneakers`、man6 页、
   LICENSE 与 terminfo 数据库。
5. **源码 URL 镜像列表**（R39 合规前提下的可达性处理）：官方源
   `github.com/bartobri/no-more-secrets` 保留（列表末位兜底），前面加
   `gh-proxy.com` / `ghproxy.net` 镜像——CI worker 直连 github.com 被阻断已
   多次实证（inform6/inheritenv 首轮 conan-build-test 失败）。三源实测
   25251 B、sha256 逐字节一致（`4422e59b…cb1b`），L0g 的 github 告警由
   镜像列表消解。gitcode 镜像不可用（实测 200 但仅回 5793 B 非 tar 包）。

## terminfo 数据库（本版新增）
- 来源：`ncurses/6.4` 依赖包的 `share/terminfo`（该配方 `_validate_package()`
  强制其存在）。
- 安装位置：`<package>/share/terminfo`；`package_info()` 中
  `runenv_info.define_path("TERMINFO"/"TERMINFO_DIRS", <pkg>/share/terminfo)`，
  消费方经 `conanrun` 环境即得到可用终端数据库。
- 测试侧：harness 显式传 `TERM=ansi|ansi 可用的等价条目` + `TERMINFO` 指向
  包内数据库，并在 pty 下实跑（不依赖宿主系统 terminfo 是否完整）。

## 编译命令（等价于配方 build()）
```sh
make -j1 CC=clang CFLAGS="-fPIC -O2 -I<ncurses include>" \
     LDFLAGS="-L<ncurses lib>" all-ncurses
```

## 验证
- `nms -v` → `nms version 1.0.1`（非交互干净退出，不触发 ncurses 初始化）
- `nms -a`（真实终端）：提示 `Enter input:` → 输入文本 → 特效逐字解密出该文本 →
  末尾按键退出码 0
- `sneakers`（真实终端）：渲染 `FEDERAL RESERVE TRANSFER NODE` 面板 → 按键退出码 0
- 负向路径：空输入 → `Input is empty`（非 0）；`-Z` → `Unknown option`（非 0）；
  `sneakers` 非 tty → `Input not from an interactive terminal`（exit 1）
- 负向注入控制：截断后的 `nms` 必须被同一条版本检查判失败；抽掉随包
  terminfo 数据库后运行必须失败（宿主 terminfo 完整时该条以 SKIP 记录）
- 上游无测试套件（`make -n check` 无该目标），消费者测试见 test_package/

### AArch64 真机实测记录（HarmonyOS PC，2026-09-26）

`python3 test_package/nms_pty_test.py <package_folder>`：**36 条断言全过，0 失败，
5 条仅在真实 pty 下可跑的检查跳过**。跳过的原因是本机沙箱拒绝该用户打开
/dev/ptmx（`out of pty devices`），效果通路因此改由管道段覆盖（含多行输入：
两行文本必须落在相邻行，第 5 节）—— 这一版把 1.0.1 配方只跑 `nms -v` 的缺口
补上了，特效代码真机跑到了。

真机上摸到的四件事，决定了这条测试怎么写：

1. **明文不在字节流里，且回放器必须实现完整的 CSI。** ncurses 的 jumble/reveal
   循环每轮先刷掩码、再逐字符原位覆盖，而且**不是从左到右画的**：每个字符前面
   都可能先来一条定位（`\r` + `\x1b[<r>d`、`\x1b[<r>;<c>H`、`\x1b[<c>G`、`\x1b[C`、
   `\b`）。`grep` 原始抓包和"剥掉转义"后的抓包都找不到明文——它只作为终端状态
   存在，所以断言走一个最小终端仿真。回放器漏掉其中任何一条定位命令，其后每个
   字符都会错位一格：本版起初只认 `H/f/d/G/J` 五个 CSI，漏了 `\x1b[C`（前移），
   于是把真机屏幕上的 `TOP SECRET DATA` 读成 `O╜P SECRET DATA`，官方校验两次报
   "效果没有渲染出输入"。修法：按 ECMA-48 完整解析 CSI（参数字节 + 中间字节 +
   0x40..0x7e 终结字节）并实现移动(A/B/C/D/E/F/G/`/a/d/e/H/f)与擦除(J/K/X) 一套
   命令；约定（一字符一格、`\x1b[2J` 不移动光标、C1 控制字符不占格、序列被截断即
   停止回放）与独立实现 pyte 逐格对齐：真机抓包 24x80 全等，29 条惯用法用例与
   抓包的 2661 个前缀截断点全部 0 差异。`--selftest` 里的 screen selftest
   （11 条惯用法，真机 PASS）用来把"回放坏了"与"程序坏了"分开。
2. **收尾按键源自 /dev/tty，不是管道。** `nmstermio_init_terminal()` 在 stdin 不是
   tty 时执行 `freopen("/dev/tty","r",stdin)`，且等按键前还有一次
   `nmstermio_clear_input()`（flushinp）。管道跑法既没有控制终端可答、按键又会被
   清掉，于是进程停住不走；它同时捕获 SIGTERM，`timeout(1)` 于是永久等待。
   测试对此如实处理：效果渲染完整后由测试收尾并以注记说明，退出 0 这条强断言交给
   pty 段把守；收尾一律 kill -9 + 有界读，不再出现无界阻塞
   （此前无界的 `p.stdout.read()` 曾把整条测试挂死两次，已修）。
3. **随包 terminfo 是承重的。** 抽掉 share/terminfo 后同一条管道运行非 0 退出、
   渲染不出任何明文；截断的二进制在同一条版本检查上被判定失败 —— 两条负向注入
   控制都真机通过。
4. **同一性质也适用于 sneakers 面板：CI 的字节 grep 断言失败，改成断言回放屏幕。**
   `sneakers` 先把 20 行面板拼成一个字符串再调 `nmseffect_exec()`，走的是同一台
   逐格重绘引擎，所以面板文本同样**不是抓包的字节子串** —— 该断言是 pty 专有的
   （真机恰好跳过），CI 是第一个跑它的主机，实测原始字节里既没有
   `FEDERAL RESERVE TRANSFER NODE` 也没有被断言的英文行；把断言改为
   `shows_text(render_screen(out), ...)` 后 CI 侧通过。同时补了一条**不依赖 pty**
   的多行输入断言（第 5 节：两行密钥必须渲染在相邻两行），让同一套回放机制在
   没有 pty 的主机上也跑到；真机抓包（23505 B）复核：明文不在字节里，回放与
   pyte 逐格一致地读出两行。

### 官方校验（conan-verify，真机，2026-09-26 19:58）

`python3 scripts/ohc-run.py conan-verify no-more-secrets 1.0.1.1` → **Verdict: PASS**，
G0/G1/G2/G3/G4/L2/L4/L5 全过，结论行 `可标记 status: published`。报告
`reports/conan-verify-report.md`；构建与测试全文 `reports/conan-create.log`，其中
G2 的 test_package 就是本 harness：**36 条断言 0 失败 5 跳过**，效果断言
`exact; screen: ['TOP SECRET DATA']`，多行断言
`got rows 0/1; screen: ['ALPHA BRAVO CHARLIE DELTA ECHO FOXTROT GOLF HOTEL INDIA JULIETT KILO LIMA', 'SECOND ROW TEXT']`。
校验流程会临时向 `conandata.yml` 注入 GitHub 镜像再恢复，实测校验前后 md5
一致（`b4abe2c1c2ebd367aab77d65504f2aa3`，1219 B）。

（本轮为第二次校验：首次校验后 CI 报出 sneakers 面板的字节 grep 断言失败，
harness 已按其根因改为断言回放屏幕并补多行断言，见上节第 4 条，随后重跑本
校验以刷新证据。）

## 关键命令
- conan create: 见 conanfile.py（requirement ncurses/6.4）
- 消费者测试: `python3 test_package/nms_pty_test.py <package_folder>`
---

**编译结束**: 2026-09-26
**最终状态**: built
