# nuvie 0.5 — 无 CLI 的交互式程序在无显示设备 CI 上的可验证断言（草稿）

**Category**: testing, conan, ohos, ci · **Severity**: 2 · **Tool**: conan/sh

## 症状

游戏 / 全屏应用类上游通常**没有** `--version` / `--help`，`main()` 直接进 SDL
事件循环。在 CI 沙箱（无显示设备、无游戏数据）里天真地 `run "$BIN"` 会：

- 挂死在事件循环里（CI 卡到超时），或
- 行为不确定（取决于该 worker 碰巧有没有视频驱动）。

于是移植者退化成两条错路：

1. 编译一个 print-only 的 stub 来"跑" —— 跑的不是打包产物，不构成 R34 要求的
   「对真实二进制实跑」；
2. 用 `readelf` / `file` / 字符串扫描二进制来"验证" —— 根本没执行任何代码，
   且与工具链实现细节耦合。

难点不是"跑起来"，而是：**在没有显示设备、没有游戏数据、没有 CLI 参数可借的约束下，
找出一条一定能走到、且一定自行退出的执行路径。**

## 处置（可复用）

### 1. 读源码，找「初始化失败早期 return」的分支

条件是：它必须发生在**设置交互式暂停点 / 进入事件循环之前**。

nuvie 的实例 —— `main()` 在 `init() == false` 时是：

```c
if(nuvie->init(argc, argv) == false)
{
  ConsolePause();
  return 1;
}
```

而 `ConsolePause()` 的第一句就是：

```c
void ConsolePause()
{
	if(g_console == NULL)
		return;          // ← Console.cpp:113-114
	...SDL_PollEvent 循环...
}
```

`g_console` **只在 `ConsoleInit()` 之后才非空**，而 `ConsoleInit()` 排在
`initConfig()` 与 `screen->init()` 之后（nuvie.cpp:138）。于是：
**`ConsoleInit()` 之前的失败路径必然立即返回、以退出码 1 结束，不会挂死。**

> ⚠️ 但**不要**把这条当作「所有可用的失败路径都在 ConsoleInit 之前」。
> nuvie 里 `initConfig()` 失败（路径 B）确实在 `ConsoleInit()` 之前；但
> `screen->init()` 成功、之后 `checkGameDir()` 失败（路径 C 实测走的就是这条）
> 是在 **`ConsoleInit()` 之后**才 `return false` 的 —— 此时 `g_console` 已非空，
> `ConsolePause()` 会真的进事件循环。本包实测该进程仍自行退出（rc=1），但这是
> **观测结果而非源码可证**，所以必须叠一个有界运行器兜底（见 §4.2）。
> 教训：**「哪条失败路径在暂停点之前」要一条一条按源码行号落实，不能一句话概括。**

读源码时务必顺带确认**失败路径不会先去调未初始化对象** —— nuvie 里
`ConsoleAddInfo` / `ConsoleAddError` 都自带 `if(g_console != NULL)` 守卫，
所以提前调用是安全的空操作。这一点要**逐处核对**，不能想当然。

### 2. 用环境变量驱动到目标路径 —— 但别假设"设个假驱动就让 SDL_Init 失败"

| 路径 | 驱动方式 | 走到哪里 |
|---|---|---|
| B | `( unset HOME; exec "$BIN" )` + cwd 无配置文件 | `initConfig()` 失败 → `No config file found!`（ConsoleInit 之前，rc=1 可证） |
| C | `HOME=<可写空目录>` + `SDL_VIDEODRIVER=<不存在的驱动>` | 配置写出并读回 → 进入 `new Screen` / `Screen::init()` / `set_screen_mode()` |

路径 B 的**前提**：源码对 HOME 未设置做了显式守卫
（`nuvie.cpp:279` `if(home_env != NULL && initDefaultConfigUnix(home_env))`）——
否则 unset HOME 会变成空指针解引用。**这一条必须读源码确认。**

> ⚠️ **本 PR 踩到的坑**：一开始把路径 C 写死成「`SDL_VIDEODRIVER` 指向不存在的
> 驱动 ⇒ `SDL_Init(SDL_INIT_VIDEO)` 返回负值 ⇒ 打印 `Couldn't initialize SDL:`」。
> 在 OHOS 的 sdl12-compat 上**不成立**：`SDL_Init(SDL_INIT_VIDEO)` 对未知
> `SDL_VIDEODRIVER` **不返回负值**，进程继续跑到 `Screen::set_screen_mode()`，
> 打印 `Attempting to set vid mode:`，于是既不打印 `Couldn't initialize SDL:`、
> 也不打印 `Initializing screen!`（后者只在 `screen->init()` 返回 false 时打印）。
> 写死单条文案的断言直接 FAIL。
>
> 教训：**假环境变量不是"确定性失败开关"**，它只是把进程引到某段代码；
> 到底在这段代码的哪个分支退出，是**平台相关**的。对"走到了某段代码"这类判据，
> 用 **`check_any`**（列出该段可能打印的若干文案，命中任一即通过），
> **不要**写死某一条。

### 3. 断言挑「只能由真实执行产生的可观测输出」+ 反例断言

- 启动日志（证明 `main()` 真的跑了）：`Debugging enabled`
- 到达目标代码段（证明执行流进去了）：`No config file found!`（B）/
  `Loading Config from` + `check_any`（C：`Attempting to set vid mode:` /
  `Couldn't initialize SDL:` / `Initializing screen!` / `Unable to create surface`）
- **`check_not` / `check_none` 反例**：断言 stderr 里**没有**
  `cannot open shared object`、没有 `undefined symbol`、
  没有 `Error loading shared library` / `Error relocating`。

反例把「动态加载器 / 符号解析失败」（那是退出码 126/127 与**另一种 stderr
文本**）与「程序自己正常走到失败分支」（退出码 1）严格区分开 ——
这是鸿蒙特有测试最核心、最可证伪的判据。**正向判据用 `check_any` 放宽到
"到达该代码段"，反例判据用 `check_not` 收紧到"没有任何加载器错误"**，
一宽一紧恰好在平台差异与可证伪性之间取得平衡。

### 4. 两个工程细节（都是踩过的坑）

1. **不要用 `set -e`**：脚本要后台起进程再按秒轮询，`set -e` 会让 `wait` 的非零
   返回直接终止脚本，而不是记一条 FAIL。改用显式 `ok`/`bad` 计数函数 + 末尾统一判定。
2. **叠一个有界运行器**：`"$@" >out 2>&1 &` + `kill -0` 轮询 N 秒，超时 `kill -9`
   并返回 124。它把「上游将来行为变化导致挂死」从 **CI 永久卡住**降级成**一条 FAIL**。

另外：**不要**做 `readelf` / `file` / 字符串扫描这类二进制静态属性检查 ——
断言写在可观测运行行为（stderr 文本 + 退出码）上。

### 5. 把路径 C 的真实输出 dump 进 CI 日志（`#` 前缀，不参与判定）

对"文案随平台分支而异"的路径，断言本身只能写宽（`check_any`），但**排障需要
看到真实输出**。用一个 TAP 诊断块把整份 stderr 带进 CI 日志：

```sh
echo "# --- path C (HOME writable) actual output ---"
while IFS= read -r _line; do echo "# $_line"; done < cinfo.out
```

`#` 开头的行按 TAP 约定不参与 ok/not-ok 判定，因此**不会**改变通过率，
却让下一次失败（或别人换平台复现）时无需再补一次 CI。

### 6. 未执行项如实登记

真正的主循环（需要真实显示栈）与需要版权数据（Ultima 6 原始游戏文件）的部分
写进 `MANIFEST.yml` 的 `unexecuted`，并说明**为什么不计入通过率**。

### 5. 未执行项如实登记

真正的主循环（需要真实显示栈）与需要版权数据（Ultima 6 原始游戏文件）的部分
写进 `MANIFEST.yml` 的 `unexecuted`，并说明**为什么不计入通过率**。

## 退路

- **上游连一条初始化前 return 的路径都没有**：给上游提一个上游化补丁加
  `--self-test` / `--version` 式纯文本早期出口，再对该出口写断言。
  **不要**用 print-only stub 冒充（R34），也不要改成"只要不崩就算过"。
- **必须验证真实窗口/渲染路径**：需要 CI 侧虚拟显示（Xvfb / weston headless）。
  这属于**环境**能力而非配方能力，当前 OHOS 沙箱不提供 —— 写成「未执行项」，
  不要把结论建立在它之上。

## 验证

nuvie 0.5 实测：`test_package/test_nuvie.sh` **29 条断言**，其中 B/C 两组共
**10 条为鸿蒙特有**（真实执行 OHOS aarch64 二进制）。两组退出码均为 1、未挂死
（C 组另有 30s `run_bounded` 兜底）。

> 踩坑复现（用于验证本文结论）：最初路径 C 写死断言
> `Initializing screen!` + `Couldn't initialize SDL:` —— 两条在 OHOS/sdl12-compat
> 上**都 FAIL**（进程实际走的是 `set_screen_mode()` → `Attempting to set vid mode:`）。
> 改成 `check_any` 覆盖该段全部可能文案后通过。这正说明「假 SDL_VIDEODRIVER ⇒
> SDL_Init 失败」的假设不可移植。

## 关联

- `archives/n/nuvie/0.5/test_package/{test_nuvie.sh,conanfile.py,MANIFEST.yml}`
- `archives/b/ballandpaddle/0.8.1/test_package/test_ballandpaddle.sh`
  （同类手法：借 `--version`/`--help` 在 SDL 初始化**之前** `exit(0)` 的路径）
- `knowledge/drafts/DRAFT-6380-nuvie-0.5-autotoolsdeps-vs-sdl-config-two-flag-channels.{kv,md}`
