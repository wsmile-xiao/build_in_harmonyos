# mksh 59c 适配笔记

## 编译环境
- 构建系统: custom（上游自带 Build.sh：ksh 语法脚本，conftest 特性探测 + 编译链接 + 生成 test.sh，不经 configure/make）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，profile ohos-aarch64）
- 状态: built
- worktree: /storage/Users/currentUser/ws/worktrees/mksh-59c，分支 feat/mksh-59c
- 上游源: mksh-R59c.tgz → 2026-09-23 换源后为 GitHub tag 归档 `mirabilos/mksh-cvs2git@mksh-R59c`（peel 提交 8b6f1b53…，解包树与原版发行物 `diff -rq` 完全一致；归档 sha256 f9d437710bc75de84fdd226508f5855a0f7d2d766679a3fff1d2fec803bb8859）。原源 mbsd.evolvis.org 与官方主站 mirbsd.org 连续两轮 CI Worker 下载失败（build #56618 / #56997，机器人诊断均为网络问题）后按用户裁定换源；原版发行物锚定 sha256 77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506（与 Fedora koji 源 rpm 的 tarball 双源一致）仍然有效

## 版本串口径

上游版本串 59c 无点（R54c 同形态字母后缀），发行物文件名带 R 前缀 `mksh-R59c.tgz`。
三处同源印证：sh.h `MKSH_VERSION "MKSH 59c"`；构建注入 `-DMKSH_BUILD_R=593`；
产物自报 `KSH_VERSION=@(#)MIRBSD KSH R59 2020/10/31`。

## 编译步骤

conan create archives/m/mksh/59c -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

配方要点：build() 用 AutotoolsToolchain.vars() 取交叉 CC 后**内联**驱动
`sh Build.sh -r -j -Q`（mksh 无 configure/make；smstools 同款 refusing-PATH-clang
口径）；CFLAGS 追加 `-fstack-protector-strong -fPIE`、LDFLAGS 追加
`-pie -Wl,-z,relro -Wl,-z,now`（L4：PIE/RELRO/BIND_NOW，Build.sh 默认仅 -O2）；
`TARGET_OS=Linux` 必须经环境显式传入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | TARGET_OS 不设（uname -s=HarmonyOS 落 Build.sh unknown 分支）时仅得 "may or may not work" 警告继续，首次构建还出现 setresuid/setresgid 隐式函数声明告警（复跑未复现——unknown 分支 conftest 判定存在轮间波动，revoke/setres 探针两次构建结果不同） | unknown 分支缺 Linux 口径的 `-D_GNU_SOURCE`（musl 系这两个声明依赖它）且判定不稳定 | 显式 `TARGET_OS=Linux`（OHOS=Linux 内核+musl；与上游 Android→Linux 映射同口径）。修后三次构建全部 0 告警、conftest 结果稳定 |
| 2 | 首跑 check.t 85 例假失败：stderr 首字符为 `/`（报错行以绝对路径开头）、here-doc/here-string 类成片 exit 1 | OHOS `/tmp` 只读，mksh 的 here-doc/here-string 临时文件走 `$TMPDIR`（缺省 /tmp 即失败）；而 check.pl 只把 HOME/PATH 等白名单变量透传给用例子进程，TMPDIR 不在其中 | check.pl 唯一环境注入开关 `-e e=v`：`./test.sh -e TMPDIR=<可写目录>`。修后 85→32 例失败 |
| 3 | history-* 等 32 例失败：`can't find tty fd: No such device or address` | 这些用例带 `need-ctty: yes`（history/job-control 类，需控制终端）；自动化环境无 ctty | 上游开关：`./test.sh -C regress:no-ctty`（check.t 自述的无 ctty 关闭方式，check.pl category_check 官方处理路径）。修后 32→2 例失败 |
| 4 | regression-63/pipeline-3 两例：expected-stderr 为空但实测多一行 `fgrep: warning: fgrep is obsolescent; using grep -F` | 宿主 GNU grep 3.12 的 fgrep 每次打印弃用告警；用例断言假设 fgrep 历史契约（静默 grep -F） | 测试期 PATH 前置 shim：`fgrep` → `exec grep -F "$@"`（仅测试用，不进包、不改全局）。注意 test.sh 把 Build.sh 运行期 PATH **冻结**进自身，故 shim 必须在 Build.sh 之前进 PATH。修后 2→0 例失败 |
| 5 | mksh 无 `--version`/`--help`/`-V`，全部 rc=1 | mksh 只有一组短选项（-c/-s/-i/-h 等），无 GNU 长选项惯例 | smoke/取证口径：`mksh -h` 是合法旗标（hashall），空 stdin 下 rc=0；版本自报用 `mksh -c 'echo $KSH_VERSION'` |

## 上游测试（check.t 回归套件）

```bash
# 静态清点 N（上游唯一回归测试集，R59c 原包）
grep -c '^name:' check.t          # 604
# 实跑取数（conan create 日志内，Build.sh 之后）
./test.sh -C regress:no-ctty -e TMPDIR=<tmpdir>
#   → Total failed: 0 / Total passed: 530
```

四分项：**TOTAL 604 = PASS 530 + FAIL 0 + SKIP 74 + NOT_RUN 0**（同一统计单位：
check.t `name:` 用例；test_package 消费者断言分栏另计，不进上游分母）。

74 个 SKIP 逐桶归因（**主因归因口径**：check.pl category_check 的执行序为
need-ctty 先判 42 例、静态类别 32 例；其中 history-ed-1-old/2-old/3-old 3 例
同时带 `need-ctty: yes` 与 `category: stdout-ed`（无 -C 时也会被静态类别跳过），
双重命中按主因归入 need-ctty 桶；两口径的 SKIP 总数均为 74，合计闭环不变）：
- **39 个 need-ctty**（selftest-tty-present、env-prompt、history-basic/-dups/
  -multiline/-e-minus-1..5/-list-1..7/-list-r-1..3/-subst-1..5/-ed-1..3、
  history-unlink、integer-base-err-3、regression-50/52、xxx-exec-1、
  xxx-status-1、mkshrc-2b、persist-history-1、utf8opt-2/3b、event-subst-0）：
  依赖控制终端，自动化环境无 ctty，按 check.t 自述以上游开关 `-C regress:no-ctty`
  关闭。替代验证：同族非 ctty 用例全绿 + test_package 消费者断言覆盖实际执行路径。
- **35 个静态类别不适用**（check.pl category_check 按构建类别集
  `shell:legacy-no int:32 shell:textmode-no shell:binmode-yes` + 运行时
  `os:linux`/`shell:ebcdic-no` 判定）：os:mirbsd 4、os:mirbsd+os:openbsd 1、
  disabled 3、int:64 3（aarch64 int=32 位，Build.sh 生成 int:32）、stdout-ed 3、
  shell:legacy-yes 2、shell:faux-ebcdic 2、!shell:legacy-no 1、!shell:textmode-no 1、
  os:os2 1、int:u 1、binsh 1、shell:textmode-yes 1、mnbsdash 1、fastbox 1
  （仅 test.sh -f 启用）、!shell:ebcdic-no 9（非 EBCDIC 构建下 check.pl:274
  运行时定义该类别）。

消费者测试 test_mksh.sh：10 断言 10 PASS（version-string / valid-flag-h-exit-code /
arithmetic-expansion / parameter-expansion / function-call / pipeline /
command-substitution / exit-status / test-bracket-builtin / loop-redirect）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/mksh | 约 330KB | MirBSD Korn Shell 可执行（PIE+RELRO+BIND_NOW，OHOS 签名） |
| share/man/man1/mksh.1 | - | 上游手册页（Build.sh 安装指引的交付物） |
| share/mksh/dot.mkshrc | - | 上游交互配置样例（Build.sh 安装指引：/etc/skel/mkshrc） |

许可说明：mksh 发行物无独立 LICENSE 文件，许可文本（MirOS Licence）内嵌于
mksh.1 尾部与各源文件头部，故 licenses/ 目录不伪造文件，以 mksh.1 交付。

## 零依赖说明

mksh 无外部硬依赖（仅需 C 编译器与 libc）；回归测试运行器需 perl——设备与
CI worker PATH 的 `/data/service/hnp/bin/perl`（HNP，5.42.0）直接满足，不经
conan 依赖注入（避开 conan perl XS 与 HNP perl ABI 冲突坑，AGENTS §一.23）。
