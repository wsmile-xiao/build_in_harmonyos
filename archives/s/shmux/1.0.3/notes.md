# shmux 1.0.3 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 生成 configure；手写 Makefile.in，无 automake/VPATH）
- 编译日期: 2026-09-22
- 编译器: clang 15（profile: ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8）
- 状态: built（conan-verify 通过；发布态由 release 流水线确认）

## 编译步骤
1. W0 依赖检查：ncurses/6.4、pcre/8.45 均已在 ohpcd 制品仓发布（conan download --only-recipe 验证）。
2. build() 内 Python 自包含改写（`_patch_config_ohos`，无补丁文件、CI 安全）：
   - config.guess：NetBSD 锚点前插入 `*:HarmonyOS:*:*)` case，**按文件习语自适应输出块**
     （≤2016 版分支以 `echo ${MACHINE}-unknown-linux-ohos` + `exit ;;` 结尾——该文件全文无
     GUESS 变量；2018+ 才是 `GUESS=` + 文件尾 `echo "$GUESS"`）；
   - config.sub：KERNEL-OS 拆分行加 `linux-ohos*`、OS 校验列表加 `-linux-ohos*`。
3. chmod +x configure/config.guess/config.sub/install-sh（HMDFS 解包执行位）。
4. `autotools.configure()`（in-source：`folders.build = "."`，手写 Makefile.in 的
   `(cd src && make)`/`(cd tests && ./runall)` 无 VPATH 支持）→ `make -j2`。
5. R51 上游测试：`make test`（TERM=xterm + TERMINFO=<ncurses 包>/share/terminfo 注入，
   term.c 运行时 tgetent 需要）。SHMUX_SH 不全局注入——只由补丁 0001 在
   `tests/timers.sh` 内 scoped export（见问题 #5 修法①，作用域收窄防偶发 SIGSEGV）。
6. `autotools.install()`（prefix=/，DESTDIR=包目录）→ bin/shmux + share/man/man1/shmux.1
   + share/shmux/mcmd.sh。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type`（uname -s=HarmonyOS） | 上游 config.guess 快照 2016-10-02，无 OHOS/HarmonyOS 分支（E007） | build() 内插入 HarmonyOS case + config.sub 加 linux-ohos*（自包含 Python 改写） |
| 2 | 第一版补丁（GUESS= 习语，zile 0001 同款）插入后**仍报同一错误** | 老版（≤2016）config.guess 分支以 `echo <triplet>`+`exit` 结尾、全文无 GUESS 变量：赋值式分支命中后 `;;` 落空进文件尾 `cat >&2` fallback（exit 1），无任何输出 | 补丁块按文件习语自适应：无 `echo "$GUESS"` ⇒ 用 `echo …`+`exit ;;` 形态；改后 `sh config.guess` → `aarch64-unknown-linux-ohos` rc=0（详见 knowledge/drafts/DRAFT-shmux-1.0.3-config-guess-pre2018-echo-idiom-fallback） |
| 3 | conan 下载源码走 ghfast.top 镜像超时（网络抖动） | 镜像不可达时工具不回退直连 | 向 core.sources:download_cache（~/tmp/ch/dlcache/s/）按 sha256 播种官方 tarball + URL 边车 json（官方源 sha256 校验一致） |
| 4 | ncurses 为硬依赖（AC_SEARCH_LIBS tgetent 缺失即 error） | 设备无 termcap/curses/ncurses 系统库 | requires ncurses/6.4（tgetent 由其提供）；pcre/8.45 使 regex/lnregex analyzer 生效（configure 缺 pcre 仅 WARN 降级，不阻塞） |
| 5 | 上游 7 组测试中 timers/run 组假通过（`-C 2s` 超时不触发，`Summary: 4 successes` 取代期望的 `3 timeouts, 1 success`） | OHOS `/bin/sh`=hishell 不遵 POSIX「未捕获 SIGALRM 即终止」：alarm 后只打断前台 sleep，脚本继续跑到 exit 0、termsig=0（C 探针 fork+alarm+exec 实测：hishell elapsed=2s exit=0 termsig=0；hnp bash 同脚本 termsig=14 正常死）——shmux 靠子进程 WTERMSIG==SIGALRM 判超时（src/exec.c:199 / loop.c:1420,1629） | 修法①（用户拍板 2026-09-22；**2026-09-23 作用域收窄**）：上游文档化变量 `SHMUX_SH`（shmux.1 / target.c:369）指 `/data/service/hnp/bin/bash`，但**只由补丁 0001 在 `tests/timers.sh` 内 export**（唯一需要 target 被信号杀死的组），不再全局注入——实证全局注入（lnregex/regex targets 跑 hnp bash）会与 shmux 分析器路径叠出**偶发 SIGSEGV**（同机配置矩阵二分：hishell 运行态 0/13 套件零崩 vs bash 运行态 ~6/14，含前任时代 0/8；引擎/头文件/标志位三态全部排除后唯一幸存因子）。通用机制已入池 `经验文档/B草稿库/DRAFT-PKG-VER-hishell-swallows-sigalrm`（本 PR 承载 config.guess 草稿，一 PR 一知识） |
| 6 | regex/lnregex 组假红：每条正常「不匹配」打出 `Fatal error ... regexec() failed with code match failed` 并计为分析失败 | **编译/链接正则库错配（常量+标志位全错）**：conan pcre 包 package_info 全量注入 `-lpcre -lpcrecpp -lpcreposix`，-lpcreposix 排在 libc 之前把 analyzer.o 的 regcomp/regexec 解析成 pcreposix 实现；而 analyzer.c 按系统 `<regex.h>` 编译，双方**整套值域不同**——REG_NOMATCH 1↔17（pcreposix 从 REG_ASSERT=1 起数）、REG_EXTENDED 1↔0、REG_NEWLINE 4↔0x0002、REG_NOSUB 8↔0x0020 ⇒ 每次正常 no-match 落入致命分支（`regerror(17)`="match failed"，逐用例取证：Fatal 全在应无匹配处，如 `-A .` 下空 stderr），且编译标志被错解成 ICASE+NOTBOL（修前 regex 2/6、lnregex 1/3） | **先试**修剪 pcre 库注入改走系统 libc 正则：单测全绿但**套件 3/4 轮偶发 `Signal 11`**（musl regexec 对 REG_NEWLINE 用例崩溃，点位漂移 regex c4/c6 与 lnregex c2，gdb 下 0 复现的 heisenbug，隔离 40 次不现）→ **弃用**。**终案=补丁 0003**：analyzer.c `#include <regex.h>` → `#include <pcreposix.h>`，头/库配对（常量与标志位同源），引擎回到上游注入的 pcreposix；修后 regex/lnregex 全绿、Fatal=0、无 Signal |
| 7 | run 组 0/1：`Analyzer for 3 timed out` 从不出现，target3 的 analyzer 跑满 sleep 后正常退出、被报成 `Analysis of 3 output indicates an error` | analyzer 子进程 fork→alarm(2)→execvp(./run)，走 tests/run 的 shebang `#! /bin/sh`=hishell 吞 SIGALRM（与 #5 同机制，但 SHMUX_SH 只管 target shell、不管 analyzer 脚本解释器）⇒ `-A 2s` analyzer 超时永不触发 | 补丁 0002 把 tests/run shebang 改指 `/data/service/hnp/bin/bash`（仅 1 行、不动断言；hnp bash 下 QC-21 探针实测 termsig=14 会死）；修后 run 1/1。风险与退路同修法①：CI worker 若无该路径则退父侧墙钟并逐用例申报 |
| 8 | test_package 断言 2/3 首跑失败（前任从未跑到消费测试）：`grep " 2 targets processed"` 带前导空格匹配不到 | 断言 grep 为起草时手写、猜了前导空格；实际格式串是 `"%d target%s processed in %d second%s."`（src/target.c:732）行首即数字（我们自己的 test 脚本 bug，非上游问题） | 去掉 grep 模式前导空格为 `"2 targets processed"`，三断言独立复跑 3/3 PASS |
| 9 | configure 报 `can't create ./confXXXX/subs1.awk: Permission denied`（E011/E114 家族，QC-21 修复） | release tarball 内预生成的 configure 用 `umask 077` 建 config.status 临时目录，HMDFS 上随后自身不可写 | build() 内 `replace_in_file` 把 `umask 077` 就地改 `022`——静态单点、本包不引入 autoreconf 自举故不留补丁文件（zile 2.6.4 同款处置；conanfile build() 注释同步记录于此） |

## 源码修改
- **patches/0001-tests-timers-export-shmux-sh.patch**（patch_type=portability）：
  `tests/timers.sh` 顶部注入 6 行（4 行注释 + `SHMUX_SH=...` + `export`），使该组
  targets 用 hnp bash（hishell 吞 SIGALRM 致超时假通过，notes #5）。**作用域收窄**：
  只动 timers.sh、不碰 runall（原方案删 runall 的 `unset` 行会让所有组 targets 跑
  hnp bash，实证与分析器路径叠出偶发 SIGSEGV——见 #5；runall/tests 其余文件保持
  原厂）。不删任何用例、不改任何断言、不引入 `#-` 行（避免干扰 runall 排序）；
  dry-run+真应用通过。
- **patches/0002-tests-run-analyzer-shebang-hnp-bash.patch**（portability）：
  `tests/run` shebang `#! /bin/sh` → `#! /data/service/hnp/bin/bash`（1 行）。analyzer
  子进程是 fork→alarm→execvp(./run) 直接走 shebang，不经 SHMUX_SH，hishell 会吞
  SIGALRM 使 `-A 2s` 超时永不触发（notes #7）。仅 run 组使用该脚本；不动任何断言；
  dry-run+真应用+反查通过。
- **patches/0003-analyzer-include-pcreposix.patch**（portability）：
  `src/analyzer.c` `#include <regex.h>` → `#include <pcreposix.h>`（1 行）。conan 注入的
  -lpcreposix 抢在 libc 前提供 regcomp/regexec，头/库必须同源（notes #6：REG_NOMATCH
  1↔17、REG_EXTENDED 1↔0、REG_NEWLINE 4↔0x0002、REG_NOSUB 8↔0x0020 全套错配）。
  改系统正则（musl）路线已实测弃用：套件级偶发 SIGSEGV。dry-run+真应用通过。
- config.guess/config.sub 改写仍在 build() 内完成（不进补丁文件），理由：
  ①CI clean 环境可复现（无外部脚本依赖）；②不携带 `__OHOS__` 宏（PF5 合规）；③习语自适应逻辑
  需要读文件判断，补丁文件形态做不到。

## 依赖版本
- ncurses/6.4（ohpcd 制品仓，tgetent/terminfo 数据库）
- pcre/8.45（ohpcd 制品仓，regex/lnregex analyzer）

## 上游测试（R51 五维账本）
- N_static = 17（**原子断言数**，Q-23 在 tag 源码逐项复核：exitcode 3 + gccbug 1 + lnregex 3 +
  mixed 2 + regex 6 + run 1 + timers 1，按各 .sh 内 printf ok/N 末位 N 计）；
  组数 N_registered = 7（tests/runall 按 `#- N` 收集：gccbug/mixed/exitcode/timers/
  lnregex/regex/run；runall 语义 exit 77=PASS）
- N_executed = 17/17（conan create 内 `make test` 真实执行，见 reports/conan-create.log）
- 未执行分类：0
- N_consumer = 3（test_package/test_shmux.sh 断言：3 目标并行 echo 往返 / Summary 计数 /
  目标 exit 7 传播）

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify shmux 1.0.3   # 2026-09-23 终版（作用域0001+0002+0003）
# G0 PASS / G1 PASS / G2 PASS(conan create + make test 原子 17/17) / G3 PASS / G4 PASS
# + L2/L4/L5；test_package: ALL 3/3 CONSUMER ASSERTIONS PASSED
# 证据: reports/conan-create.log（running test 七组全 ok、Signal 11 计数=0）
```

- 稳定性（针对曾发现的偶发 SIGSEGV，出货配置连跑复验）：同一构建目录连跑 **5× 完整
  runall 套件 = 5 GREEN / 0 BAD**（17/17 ×5，Signal 11 = 0；配置矩阵二分收口数据：
  hishell 运行态 0/13 崩 vs 全局 bash 注入 ~6/14、判别实验 bash-targets+无timers 1/5，
  最终以「作用域收窄」使 analyzer 组回归 hishell 态）。
- 复验环境：CONAN_HOME=~/tmp/ch/home-m3-shmux，构建目录 p/b/shmuxda4316f696285/b，
  脚本 ~/tmp/uc2/m3-shmux-1.0.3/{final-stab.sh,fstab-1..5.txt}。

## 注意事项
- 上游测试 timers/exitcode 含 sleep 与信号 trap，为时长敏感型用例；设备高负载时可能引入
  波动，重跑以 conan-create.log 为准。
- `make test` 需 TERM/TERMINFO（term.c 运行时 tgetent）；配方已注入，test_package 消费者
  测试同样注入（ncurses 包自带 terminfo 数据库）。
- **勿把 SHMUX_SH 全局注入回测试环境**：analyzer 组（regex/lnregex）targets 跑 hnp bash
  会触发 shmux 偶发 SIGSEGV（数据见 #5）；只允许 timers.sh 内自带 export（补丁 0001）。
- 手写 Makefile.in 无 VPATH：任何重构必须保持 in-source（folders.build = "."）。
---

**编译结束**: 2026-09-23 03:09
**最终状态**: built
