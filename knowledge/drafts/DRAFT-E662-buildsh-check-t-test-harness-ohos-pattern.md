# E-DRAFT E662: Build.sh 自带构建器软件（mksh 形态）OHOS 适配套路

- **触发实例**：mksh 59c 全新包适配（2026-09-22，任务 mksh-59c，分支 feat/mksh-59c）
- **同族范围**：一切"自带 Build.sh/自写构建器 + 构建期生成测试入口 + perl 测试运行器"的软件（mksh/lksh 同构）
- **类别**：custom 构建形态 / 测试宿主环境 / 计数口径
- **严重度**：2（套路固定、四坑独立叠加、均可确定性复现）

> 实测读数已回填（2026-09-22，设备 conan create 干净轮 + `repro-e662-buildsh-pattern.sh`）；
> 逐字日志留档 `$HOME/tmp/mksh-59c/src/mksh/test-run{,2,3,5}.log`、
> `$HOME/tmp/mksh-59c/probe-conan-create.log`。

## 症状（四类；①③④独立于②叠加）

1. 【首次构建实测、复跑未复现】不设 `TARGET_OS` 构建时 misc.c 报
   `setresuid`/`setresgid` 隐式函数声明告警（clang 15 仅告警；clang>=16 为硬
   错误，是潜伏的 CI 时间 bomb）。unknown 分支的 conftest 判定存在**轮间波动**
   （revoke/setresugid 声明探针两次构建结果不同），`TARGET_OS=Linux` 配置下
   三次构建全部 0 告警、结果稳定。
2. check.t 首跑 **85 例假失败**：here-doc/here-string 类成片
   `unexpected exit status 256 (exit-code 1)`，失败用例 stderr 首字符为 `/`
   （mksh 报错行以 argv[0] 绝对路径开头）。
3. `history-*` 等 32 例失败：`mksh: can't find tty fd: No such device or address`
   + `warning: won't have full job control`。
4. `regression-63`/`pipeline-3` 两例：expected-stderr 为空却实测多一行
   `fgrep: warning: fgrep is obsolescent; using grep -F`。

## 根因（对应四类）

### ① TARGET_OS 缺省落 unknown 分支：丢 `-D_GNU_SOURCE` 且判定不稳定

Build.sh 缺省 `TARGET_OS=$(uname -s)`；OHOS 上是 `HarmonyOS`，落在 unknown 分支
（仅打 `; it may or may not work` 警告继续）。Linux 分支才注入
`-D_GNU_SOURCE`（musl 系 setresuid/setresgid 声明依赖它，首次构建即出现隐式
声明告警）与 `-DSETUID_CAN_FAIL_WITH_EAGAIN`。与上游把 Android 映射成 Linux
同口径，OHOS（Linux 内核 + musl）应显式 `TARGET_OS=Linux`——Build.sh 只在值
为空时才回退 uname，显式传值即被尊重；实测该配置下 conftest 判定与告警面
完全稳定（unknown 分支两次复跑间 revoke/setres 探针判定翻转）。

### ② check.pl 给用例子进程的环境是白名单，TMPDIR 不在其中

OHOS `/tmp` 只读；mksh 的 here-doc/here-string 临时文件走 `$TMPDIR`
（缺省 `MKSH_DEFAULT_TMPDIR "/tmp"`）。check.pl 的 `%new_env` 只透传
HOME/LD_LIBRARY_PATH/LOCPATH/LOGNAME/PATH/PERLIO/SHELL/UNIXMODE/UNIXROOT/USER，
自己的 `-T` 只管它自身临时文件 ⇒ 用例子进程拿不到 TMPDIR，85 例假失败。
上游预留的唯一环境注入开关：`check.pl -e e=v`（test.sh 转发 `-e TMPDIR=…`）。

### ③ need-ctty 用例在无终端环境必失败，官方豁免是 `-C regress:no-ctty`

`history-*`/job-control 类用例带 `need-ctty: yes`；check.t 自述自动化环境用
`-C regress:no-ctty` 关闭（check.pl `category_check` 对 need-ctty 的官方处理
路径，跳过**不计入实跑分母**）。SKIP 集合须逐名归因（39 例）。

### ④ test.sh 冻结构建期 PATH + GNU fgrep 弃用告警

test.sh 由 Build.sh **生成**，首行 `PATH='<构建期 PATH>'; export`——测试宿主
工具的 shim 必须在跑 Build.sh **之前**就位于 PATH，事后改 PATH 无效。
GNU grep>=3.8 的 fgrep 每次打印弃用告警，污染 expected-stderr 为空的用例；
`exec grep -F "$@"` shim 恢复 fgrep 历史契约即可（2 例恢复）。

## 解决方案（配方四件事）

```python
# build() 内（mksh/59c 配方为可工作先例）
shim = os.path.join(src, ".ohos-test-shim")   # fgrep -> exec grep -F "$@"
tmpd = os.path.join(src, ".ohos-test-tmp")
self.run(f'PATH="{shim}:$PATH" CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" '
         f'TMPDIR="{tmpd}" TARGET_OS=Linux sh ./Build.sh -r -j -Q', cwd=src)
self.run(f'PATH="{shim}:$PATH" TMPDIR="{tmpd}" '
         f'./test.sh -C regress:no-ctty -e TMPDIR="{tmpd}"', cwd=src)
```

- CC/CFLAGS/LDFLAGS 取自 `AutotoolsToolchain(self).vars()`（refusing PATH 偶遇
  clang）；CFLAGS 补 `-fstack-protector-strong -fPIE`、LDFLAGS 补
  `-pie -Wl,-z,relro -Wl,-z,now`（Build.sh 默认仅 -O2，L4 需要 PIE/RELRO/BIND_NOW）。
- perl 依赖由设备/CI worker PATH 的 `/data/service/hnp/bin/perl`（HNP）满足，
  **不经 conan tool_requires**（避开 conan perl XS ABI 冲突坑）。
- smoke 探针：mksh 无 `--version`/`--help`/`-V`（全 rc=1）；`-h` 是合法旗标
  （hashall，空 stdin rc=0）；版本取证 `mksh -c 'echo $KSH_VERSION'`
  （59c 自报 `@(#)MIRBSD KSH R59 2020/10/31`，sh.h `MKSH_BUILD_R=593` 三处同源）。

## 计数口径（604 = 530 + 0 + 74）

`grep -c '^name:' check.t` = 604（上游唯一回归测试集的静态计数 N）；
实跑 530 PASS / 0 FAIL；74 SKIP = 39 need-ctty（-C regress:no-ctty）
+ 35 静态类别不适用（os:mirbsd 4+1、disabled 3、int:64 3、stdout-ed 3、
shell:legacy-yes 2、shell:faux-ebcdic 2、!shell:legacy-no 1、!shell:textmode-no 1、
os:os2 1、int:u 1、binsh 1、shell:textmode-yes 1、mnbsdash 1、fastbox 1、
!shell:ebcdic-no 9——非 EBCDIC 构建下 check.pl:274 运行时定义
`shell:ebcdic-no`）。合计必须闭环到 604，消费者断言分栏另计。

## 复现命令

```sh
TASK_DIR=$HOME/tmp/mksh-59c; sh "$TASK_DIR/repro-e662-buildsh-pattern.sh"
```
