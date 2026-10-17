# DRAFT-rungetty-1.2-tcflsh-eacces-on-owned-pty-slave

> OHOS 上 `ioctl(TCFLSH)` / `tcflush()` 在**自己打开、且已成为控制终端**的 pty 从端上仍返回
> **EACCES(13)**，而 Linux 返回 0 ⇒ 依赖清缓冲的 getty / 终端会话类程序必降级。
> 附带一条方法学判据：判 TTY 类 ioctl 的支持度**必须先 `setsid()` 取会话首进程身份**，
> 否则在父会话里测得的 EPERM 会被误判成"平台不支持"。
> 宿主证据 = rungetty 1.2（平台任务 10319，A 机鸿蒙 PC 真机 139 行探针）。

## 症状（真机原始读数，全文见本包 `notes.md` 附录 A）

```
--- pty slave, parent session: fd=4 sid=31057 ---
tcgetattr ret=0 | tcsetattr(TCSANOW,B9600) ret=0 | cfsetispeed(B19200) ret=0
ioctl(TIOCSCTTY,1)   ret=-1 errno=1  Operation not permitted   EPERM:permission
ioctl(TCFLSH,TCIOFLUSH) ret=-1 errno=13 Permission denied      EACCES:permission

--- pty slave, new session leader: fd=4 sid=31173 (setsid()=31173) ---
ioctl(TIOCSCTTY,1)   ret=0  OK                       ← 控制终端接管能力【存在】
ioctl(TCFLSH,TCIOFLUSH) ret=-1 errno=13 Permission denied  EACCES:permission   ← 成为 ctty 后仍旧 EACCES
ioctl(TCFLSH,0)      ret=-1 errno=13 Permission denied      EACCES:permission
```

即：清缓冲操作**既不受会话身份影响，也不受是否持有控制终端影响**，稳定 EACCES；
同一段 fd 上 `tcgetattr`/`tcsetattr`/`cfsetispeed` 全部正常 ⇒ 不是 fd 失效、不是权限上下文漂移。

## 根因与影响面

平台对 tty _LINE  discipline 的 `TCFLSH` 命令做了准入限制（对照：`TIOCSCTTY` 放行、`TIOCCONS` 与
`TCFLSH` 拒），属**能力面偏差**而非配置项。落在代码上：`rungetty.c:305` 与 `:594` 两处
`ioctl(0, TCFLSH, *)（:305 传 0=TCIFLUSH、:594 传 2=TCIOFLUSH）` 必然失败；上游未检查返回值 ⇒ 行为降级（登录前清不掉缓冲）而非崩溃，
所以**不会被任何"退出码为 0"的检查发现**，只能靠能力探针定性。

## 最小复现（≤30 行即可，无需三方库）

1. `posix_openpt(O_RDWR|O_NOCTTY)` + `grantpt` + `unlockpt` + `ptsname` → 打开从端得 `fd`（本包实测全 0）。
2. 分支 A（父会话内）：对 `fd` 调 `ioctl(TIOCSCTTY,1)` → **EPERM**；`ioctl(TCFLSH,TCIOFLUSH)` → **EACCES**。
3. 分支 B（`fork()` 后子进程内 `setsid()`）：再调 `ioctl(TIOCSCTTY,1)` → **0（成功）**；
   但 `ioctl(TCFLSH,*)` **仍 EACCES**。
⇒ 两个分支对比就是本条知识的判据：**TIOCSCTTY 的 EPERM 是"无资格"，TCFLSH 的 EACCES 才是"平台不给"**。

## 已试过的失败方案

- 只在父会话里测一次 EPERM 就下结论"OHOS 不支持 TIOCSCTTY"：**错判**，本包探针第一轮就是这么错的，
  补 `setsid()` 臂后被推翻（留痕见本包 `notes.md` 附录 C 方法学自我更正）。
- 用 `tcflush(fd, TCIOFLUSH)` 替代裸 `ioctl(TCFLSH)`：同样 EACCES（libc 只是包装）。
- 改 `O_NOCTTY` 标志、改打开 `/dev/pts/N` 从端 vs 主端：结果不变。
- 为过门而 stub 掉这两处调用：等于篡改上游语义，弃（本包保留调用、只如实记失败）。

## 适用面（已验证 + 已排除）

- 已验证：rungetty 1.2（两处 `TCFLSH`）；pty 从端与控制终端接管路径。
- 同病人群：任何登录/终端管理类程序（getty 族、`mingetty`/`agetty` 变体、终端复用与串口会话工具）
  中"清缓冲"语义会静默失效；写测试时**不要**把 `TCFLSH` 成功当作可用性判据。
- 与既有条目的**矛盾登记**：E245 的处方主张「可 `syscall(SYS_vhangup)` 直调」，本包真机证伪——fork 子进程按号直调的子进程被 **SIGSYS(31) 击杀**，合入件 `agetty/2.42.2` 的 `src/ohos-utmpx-shim.c:19-22` 正是按该处方实现 ⇒ **E245 处方需复核**（本 PR 已在其 `conflicts_with` 登记，并拟经 Issue/E245 整改渠道留一条更正）。
- 已排除：`tcgetattr`/`tcsetattr`/`cfsetispeed` 与 pty 建立全链路（本包实测均正常，勿套用本条）；
  `vhangup` 与其 SIGSYS 行为属 **E245 / E246 / E051** 覆盖面（`agetty/2.42.2` 已按该路线做过 shim），本条不重复申报。

## 查重与新增价值

`TCFLSH` 在 适配经验汇总 / 经验库 / 适配检查清单 / OHOS行为探针清单 / B草稿库 与仓库 `knowledge/`
目录内**没有任何行为性条目**（仅 strace / audit / man-pages 的 ioctl 名字表命中，属枚举表非知识）；
既有条目 E245/E246/E051 讲的是 `vhangup` 与 seccomp/SIGSYS 面，与本条不同命令、不同判定路径。
新增价值 = 一条可复算的**两分支判据**（父会话 vs `setsid` 会话首进程），既给出"哪个 tty 命令被平台拒绝"，
也堵住"拿无资格时的 EPERM 当平台不支持"这类误判。

## 关联

- Issue：#3409（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3409）
- 平台任务：10319；分支：`feat/rungetty-1.2`；构建机：A 机鸿蒙 PC
- 探针源码与原始读数：本包 `archives/r/rungetty/1.2/notes.md` 附录 A/B/C（`.gitignore` 忽略 `reports/`，故随 notes 入库）
