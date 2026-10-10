# OHOS musl 缺 POSIX 线程取消 API（pthread_cancel 族）的适配（知识库拓展）

> 样例库：`archives/x/xmcd/3.3.2`（xmcd 3.3.2，Motif CD 播放器/抓轨套件）
> 同 PR 交付；检测脚本 + 复现脚本位于本目录，知识条目位于 `knowledge/drafts/`

## 1. 一句话

OHOS 的 musl libc **不导出** `pthread_cancel(3)` / `pthread_setcancelstate(3)` /
`pthread_setcanceltype(3)`，且 sysroot 的 `libpthread.a` 是**空壳**（0 个定义符号）——
`-lpthread` 补不了缺口。共性解法是**源码侧特性宏间接层**：自中止路径回退
`pthread_exit()`（语义等价），跨线程取消点按语义降级（记录 + 空操作，交由后续
`stop`/`join` 收管线），并由配方以编译期宏开关切换（缺省即上游原行为）。

## 2. 触发场景（何时该读本拓展）

| # | 现场现象 | 判定 |
|---|---------|------|
| 1 | 链接报 `undefined symbol: pthread_cancel` / `pthread_setcancelstate` | 命中 |
| 2 | 编译报 `implicit declaration of function 'pthread_cancel'`（且 `<pthread.h>` 已包含） | 命中 |
| 3 | 代码里出现 `PTHREAD_CANCELED` 判据，或 `pthread_cleanup_push` + `pthread_cancel` 组合 | 命中 |
| 4 | `-lpthread` 加上后仍报同一 undefined symbol | 命中（空壳库，见 §3 探针 C） |
| 5 | 代码只用 `pthread_create/join/mutex/cond` | 不命中，无需本拓展 |

## 3. 识别：规则 + 检测脚本

规则（脚本 `detect_pthread_cancel_gap.py` 的三级识别）：

- **A 类（源码侧）**：`.c/.h/.cc/.cpp` 中出现 `pthread_cancel(` /
  `pthread_setcancelstate(` / `pthread_setcanceltype(` / `pthread_testcancel(` /
  `PTHREAD_CANCELED`，并给出命中文件清单；
- **B 类（libc 探针）**：对目标 `libc.so` 跑 `nm -D --defined-only`，逐符号确认
  `pthread_cancel` 族是否存在，并同时探测**可用的替代符号**
  （`pthread_exit` / `pthread_detach` / `pthread_cond_timedwait`）；
- **C 类（空壳探针）**：由 libc 路径**向上**定位 sysroot（第一个含 `usr/lib` 的祖先
  目录），再对 `libpthread.a` 统计定义符号数——为 0 即空壳库，证明 `-lpthread` 路线
  不可行。上溯定位使 `<sysroot>/usr/lib/<triple>/libc.so`（真实 OHOS 布局）与
  `<sysroot>/usr/lib/libc.so` 两种布局都成立；探针不可用（未定位到 sysroot /
  无 `libpthread.a` / 缺 `nm`）时输出"探针不可用"而不编造结论。

```sh
# 用法（只读，无绝对路径硬编码；libc/sysroot 自动发现，可用参数或 OHOS_SDK_SYSROOT 覆盖）
python3 detect_pthread_cancel_gap.py --src <源码目录> [--libc <libc.so>] [--json]
# 退出码：0=未命中  1=命中（按 §4 策略处理）  2=参数/环境错误或探针不可用
#   （探针不可用时判定为 PROBE_UNAVAILABLE：源码确有取消点 API 使用，但 libc 符号表
#    未探到——须先用 --libc/--sysroot/OHOS_SDK_SYSROOT 指向 SDK sysroot 重跑，
#    不得据"未探到"判命中）
```

**实测证据（2026-10-04，OHOS SDK 26.0.0.18 / aarch64-linux-ohos）**：

| 探针 | 结果 |
|------|------|
| `libc.so` 动态符号表 → `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype` | **各 0（缺失）** |
| 同探针 → `pthread_exit` / `pthread_detach` / `pthread_cond_timedwait` | 各 1（存在） |
| sysroot `libpthread.a` 定义符号数 | **0（空壳）** |
| 样例库（xmcd 3.3.2）源码侧使用 | `pthread_cancel` 20+ 处、`pthread_setcancelstate` 1 处、`PTHREAD_CANCELED` 判据 1 处 |

## 4. 处理策略

**策略 S1（首选）：特性宏间接层 + 取消点语义降级**（样例：xmcd 补丁
`patches/0001-cdda_d-pthr.c.patch`、`patches/0002-cdda_d-pthr.h.patch`）

| 取消点形态 | 语义 | 处置 |
|---|---|---|
| **自中止**：错误分支 `pthread_cancel(pthread_self())`（本线程即刻退出） | 等价于"本线程终止" | 特性宏 `PTHR_SELF_ABORT(t)`：缺省 1 = `pthread_cancel(t)`；`=0` 时 `pthread_exit(NULL)`——**语义等价**，且语句形状一致，调用点无需改写 |
| **跨线程取消**：`pthread_cancel(other)` + `pthread_cleanup_push` 清理 | 期望对端线程在取消点退出并跑清理链 | 降级为**记录日志 + 空操作**：随后紧随的 `stop`/`join`/标志位收管线（样例 `cdda_pthr_kill` 的唯一调用者即心跳超时路径，其后立刻 `cdda_pthr_stop`） |
| `pthread_setcancelstate/type`（配置性，非取消动作） | 仅为取消做准备 | 由 `HAVE_PTHREAD_CANCEL=0` 分支整体旁路，不产生未定义符号 |

**配方侧开关**：`-DHAVE_PTHREAD_CANCEL=0`（缺省 1 = 上游原行为），补丁内**不含平台宏**，
纯特性宏——同一配方在 Linux 与 OHOS 上都可构建。

**策略 S2（次选）**：无源码可用特性宏切口时，退化为"取消点函数族静态 shim"
（在目标库内提供 `pthread_cancel` 包装实现，转发到 `pthread_exit`/标志位）——
代价是语义近似，需在 PR 说明。

**禁止（S3）**：

1. `-lpthread` / `-pthread` 顶替——sysroot 的 `libpthread.a` 为空壳，加了也解不了符号（探针 C 已证）；
2. 弱符号 stub（`__attribute__((weak))` 空实现）——会把"取消"静默变成"什么都没做"，
   运行期表现为线程不收线/资源泄漏，难排查；
3. 只加声明（`extern int pthread_cancel(pthread_t);`）——编译过、链接仍失败，问题后移。

## 5. 适用库范围

- **适用**：使用 POSIX 取消点 API 的老一代 C/C++ 库——音频/CD 抓轨（cdparanoia 系）、
  老 GStreamer 插件、部分 GUI/打印后台，以及任何把 `pthread_cancel` 当"线程自杀"用的代码。
- **不适用**：仅用 `pthread_create/join/mutex/cond` 的库（无缺口）；已自带取消点抽象或
  条件编译回退的现代库（如新 glib 在无 cancel 时走自旋+标志位）。
- **典型同族候选**：xmcd（样例，cdda_d/pthr.c）、cdparanoia、老版 libmikmod 系、
  各类 2000 年代 IRC/音乐播放器。

## 6. 限制与边界

1. **跨线程取消的语义是"近似"**：本策略用"标记 + 由对端在下次进入 stop/join 时收管线"
   替代"立即在对端取消点退出"。对端若长阻塞在不可中断路径上，退出时机会延后——需
   结合库自身的超时/心跳逻辑确认可接受（样例库有 `SIGALRM` 心跳兜底）。
2. 自中止路径回退 `pthread_exit()` 会正常执行栈上 `pthread_cleanup_push` 链，
   但**不执行**取消专用清理（`pthread_cleanup_push` 的 CANCEL 分支），实践中该类分支罕见。
3. 补丁为特性宏形态，**不含平台宏**；若上游后续版本引入了自己的取消点抽象，应优先
   复用上游开关（本拓展的检测脚本仍可用于确认缺口）。
4. 验证能力边界：CI 无显示环境，样例库以 headless 消费者用例（`cda -h`、`xmcd -h`
   抵达显示初始化）覆盖加载与运行路径；线程取消路径无法在 CI 触发真实心跳超时。
5. B/C 类证据必须由运行环境实测给出：sysroot 缺失时脚本判 `PROBE_UNAVAILABLE`
   （退出码 2），不落 HIT/MISS——"未探到"不得冒充"缺失"（误报会污染知识库置信度）。

## 7. 复现

```sh
# 识别 + 探针（输出只进日志文件，不接管道，规避 SIGPIPE）
sh reproduce.sh --src <源码目录> [--libc <libc.so>] --log ./pthread-cancel-repro.log
# 含最小链接探针（复现 undefined symbol: pthread_cancel）
sh reproduce.sh --src <源码目录>
# 连样例库一起跑（干净环境 conan create，耗时较长）
CONAN_REPRO=1 sh reproduce.sh --src <源码目录> --repo <仓库根>
```

样例库完整复现（仓库根执行，日志落文件）：

```sh
conan create archives/x/xmcd/3.3.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    > conan-create-xmcd.log 2>&1
```

## 8. 交付物清单（本拓展）

| 件 | 位置 |
|----|------|
| 问题识别规则/检测脚本 | `knowledge/drafts/musl-pthread-cancel-gap/detect_pthread_cancel_gap.py` |
| 处理策略 + 完整文档 | 本 README（第 3–4 节） |
| 复现脚本 | `knowledge/drafts/musl-pthread-cancel-gap/reproduce.sh` |
| 样例演示库 | `archives/x/xmcd/3.3.2/`（配方 + 两个补丁 + 消费者测试） |
| 知识条目①线程取消缺口 | `knowledge/drafts/DRAFT-xmcd-3.3.2-ohos-musl-missing-pthread-cancel.{kv,md}` |
| 知识条目②传统 tty 头/HZ | `knowledge/drafts/DRAFT-xmcd-3.3.2-ohos-musl-missing-termio-and-hz.{kv,md}` |

## 9. 相关

- 同族 libc 缺口：`knowledge/drafts/DRAFT-xli-1.17.0-ohos-musl-missing-rindex-bsd-legacy.*`
  （BSD 遗留函数缺口的"逐函数最小定向替换"口径，与本条的"特性宏间接层"互为正交策略）。
- 构建系统侧：`knowledge/drafts/imake-legacy-x11/`（Imake 缺失 + Makefile.std 回退，
  样例库 xli；xmcd 亦走同一路径）。
- 平台限制类：E046（chmod 不生效）、E051（未实现 syscall 排除表）。
