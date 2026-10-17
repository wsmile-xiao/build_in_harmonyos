# DRAFT-E682-sc-im-0.8.5-headless-tty-test-drive：终端类程序无控制终端的三处测试断点（rc=255 冒烟闸 / toybox env -S / valgrind 不在档）

> Contributor: 任务卡 10412（sc-im 0.8.5）| Status: Draft | Updated: 2026-09-23
> 触发场景：任务卡「领前必补：测试需 pty 模拟 tty」——实测比 pty 缺失更深：**致命 tty 假定会先打死冒烟闸**
> 对应：`knowledge/drafts/DRAFT-E682-sc-im-0.8.5-headless-tty-test-drive.kv`

## 现象（三条互不相似的报错，同一前提）

上游假定「测试者坐在一台有控制终端、有 GNU 工具的桌面前」。在鸿蒙设备/CI 上三处同时塌：

```text
# ① 致命 tty 假定 —— 每一次非交互运行都以 255 结束
$ echo GETNUM C2 | ./src/sc-im test1.sc --nocurses --nodebug --quit_afterload; echo rc=$?
81
Bad file descriptor          ← stderr，来自 read_stdin() 的 perror(NULL)
rc=255                        ← exit(-1)
$ ./src/sc-im --version >/dev/null 2>&1; echo rc=$?    # 同样 255（--help 亦然）

# ② shell 形态差 —— 上游测试入口整条失效
$ /usr/bin/env -S bash -c 'echo ok'
env: Unknown option 'S' (see "env --help")             # rc=125，/usr/bin/env 是 toybox
# 受害者：tests/run_all_tests.sh 的入口行、安装产物 src/scopen 的 shebang

# ③ 工具不在档 —— memcheck 断言全红，且套件连摘要都打不出来
$ conan list "valgrind*" -r=ohpcd | grep -c "valgrind/"
0
$ bash test1.sh
grep: test1_vallog: No such file or directory   ×8
rm: test1_vallog: No such file or directory     # set -e 在这里提前退出，assert_end 不执行
```

## 为什么 pty 不是第一步

`pty.fork()` 确实能让 ① 复原（实测输出与上游期望逐字一致），但它救不了 **冒烟闸**：

- `conan-verify` L2 与 CI L2 的判据是 `rc == 0`（`--version` 失败再试 `--help`，两者都败记 failed；
  sc-im 实测 scopen 又因②失败 → `tested=0` → **L2 FAIL** → 采信轮 rc=1，进不了 finish）。
- 采信轮/CI 都在无控制终端的进程里跑，pty 驱动只能用于**我们自己的测试驱动**，改不了闸门的读数。

所以处置次序是：**先改码（失败路径降级）→ 再补 shell 兼容 → 最后把不可得工具可选化**；
改完之后纯管道即可跑通，pty 降级为交叉核对手段。

## 根因与修法

### ① `freopen("/dev/tty")` 失败即 `exit(-1)`

sc-im `src/main.c`：

```c
void read_stdin() {
    ...
    if (f != NULL) fclose(f);                       // stdin 已被关掉
    if ( ! freopen("/dev/tty", "rw", stdin)) {
        perror(NULL);                               // → "Bad file descriptor"
        exit(-1);                                   // → rc=255
    }
}
```

`read_stdin()` 在 main 里**无条件**调用（管道读完要回控制终端继续交互），所以 `--version`/`--help`
也走到这里（二者只置 `quit_afterload=1` 并不退出）。旁支：nocurses 分支 `f = fopen("/dev/tty","rw")`
失败时 `sc_error(...)`（nocurses 下写 **stderr**）且随后 `fgetws(..., f)` 会解引用 NULL。

补丁（只动失败路径，有 TTY 时与上游逐字一致）：

```c
if ( ! freopen("/dev/tty", "rw", stdin)) {
    sc_debug("no /dev/tty available (headless), continuing");   // 不进 stderr（默认 debug=0）
    clearerr(stdin);
    put(user_conf_d, "quit_afterload", "1");                     // 主循环直接收尾 → exit_app(0)
    return;
}
```

要点：**消息必须降级**。`sc_error` 在 nocurses 下走 `ui_sc_msg` 的 stderr 分支，会往输出里塞一行，
而上游 assert.sh 是整串精确比对 —— 修了 rc 却留一行杂散输出，断言照样全红。

收益链：`--version`/`--help` rc=0 → L2 闸绿 → 上游 11 条功能断言**在纯管道下**即 PASS。

### ② `#!/usr/bin/env -S bash -a`

`-S` 是 coreutils env 的特性（拆分单参数里的选项），toybox env 没有。改 `#!/usr/bin/env bash`
（`-a`=allexport，对脚本无作用）；需要更确定时用 `#!/data/service/hnp/bin/bash`
（device-facts §一.26 的统一口径）。

### ③ valgrind 不在档：可选化 + 显式 SKIP 计数

```sh
if command -v valgrind >/dev/null 2>&1; then
    VALGRIND_CMD='valgrind -v --log-file=${NAME}_vallog ...'
else
    VALGRIND_CMD=''
fi
...
if [ -n "$VALGRIND_CMD" ]; then
    assert_iffound_notcond ${NAME}_vallog "definitely lost.*bytes" "0 bytes"   # ×8
else
    echo "SKIP[${NAME}]: 8 memcheck assertions (valgrind unavailable)"
fi
if [ "$1" != "keep-vallog" ] && [ -f ${NAME}_vallog ]; then rm ${NAME}_vallog; fi
```

**假绿面提醒**：`assert_iffound_notcond` 在 vallog *不存在* 时 `grep` 无输出 → 恰好判「通过」。
如果只是把 `VALGRIND_CMD` 置空而不包条件，套件会打印 `all 9 tests passed` —— 8 条从未执行的断言
被计成 PASS。必须用条件把它们移出执行面，并由驱动按 SKIP 行计数。

计数口径（sc-im 实测，断言调用数）：

```text
TOTAL 100 = PASS 71 + FAIL 0 + SKIP 20 + NOT_RUN 9      ← 2026-09-26 返修第二轮（替代验证后）
  PASS 71    上游原样执行的功能断言 11 + 上游断言行原样执行·替代日志来源 60（补丁 0004：
             泄漏 3 族 ← ohos-leaktrack，越界 3 族 ← AddressSanitizer 行式翻译）
  SKIP 20    未初始化 2 族 × 10：OHOS 无等价手段（无 MSan 运行时、LSan detect_leaks 不支持、
             valgrind SIGSEGV 不投递；静态分析与 -ftrivial-auto-var-init 差分均严格更弱）
  NOT_RUN 9  test7.sh-temp-disable（上游改后缀停用，tests_to_add 记载原因）

（返修前口径，本条目原始记录：TOTAL 100 = PASS 11 + FAIL 0 + SKIP 80 + NOT_RUN 9——
 80 = 每脚本 8 条 memcheck 断言 × 10，当时 valgrind 缺席且无替代手段）
```

## 驱动与证据

- 驱动：`run_upstream_tests.py`（`SCIM_TEST_PTY=0` 纯管道 / `=1` pty 交叉核对，沙箱 HOME、
  select+deadline 超时——不用 toybox `timeout`，见 device-facts §一.25）。
- 取数：`grep -cE '^\s*(assert|assert_raises|assert_iffound_notcond)\b' tests/test*.sh`（`\b` 必须有——否则 `assert_end` 汇总行被计入，同批实测 101≠100）；
  结果 JSON `$HOME/tmp/sc-im-0.8.5/upstream-tests-result-{nopty,pty}.json`。

## 关系

- 同族：`DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel`（给 pty 双通道法）、
  `DRAFT-ired-0.6-interactive-tty-wrapper-exclude-headless-l2`（无头交互脚本要排除出 L2）。
  本条补的是**改失败路径**这条路：当失败面覆盖 `--version` 时，pty 与排除法都救不了冒烟闸。
