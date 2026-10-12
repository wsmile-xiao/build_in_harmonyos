# Draft: `DRAFT-XCOLMIX-107-GUI-HEADLESS-ASSERTABLE-BRANCHES`
> Stem: `xcolmix-1.07-gui-headless-assertable-branches` — pairs with the same-stem `.kv`

# headless CI 上测 X11 GUI 程序：只断言窗口之前的分支，用关闭的回环端口强制 XOpenDisplay 失败

## 基本信息

- **ID**: DRAFT-XCOLMIX-107-GUI-HEADLESS-ASSERTABLE-BRANCHES
- **严重度**: 2（不写清楚会被当成"漏测"或"CI 卡死"）
- **类别**: testing | qemu | X11 | headless | environment
- **触发工具**: conan | make | clang | X11 | XForms | qemu
- **阶段**: testing
- **来源**: xcolmix 1.07 适配（2026-10-03，OHOS aarch64）

## 错误特征

```
In fl_initialize() [flresource.c:995]: ./xcolmix: Can't open display
qemu: uncaught target signal 11 (Segmentation fault) - core dumped
timeout: the monitored command dumped core            # 或 rc=124（阻塞）
```

## 根因

X11 GUI 程序一旦进了事件循环就会**永远阻塞**（实测 `timeout 20` → rc=124）；
显示打开失败后若代码仍继续建表单，则在解引用 NULL `Display` 时段错误
（实测 SIGSEGV / exit=139）。两者都不能当 CI 断言 —— 结果取决于 worker 上
是否恰好有可用的 `$DISPLAY`。

`xcolmix 1.07` 的 `src/xcolmix.c` 实测结构：

```c
fl_initialize (&argc, argv, "XColmix", 0, 0);   /* XForms；无 display 时返回 NULL */
if (argc > 2)              usage ();             /* ← 可断言 */
else if (argc == 2) { if (access (argv [1], R_OK)) usage (); rgbfile = argv [1]; }  /* ← 可断言 */
initforms ();
fl_show_form (colormixer, FL_PLACE_CENTER, FL_FULLBORDER, "Color Mixer");
fl_do_forms ();                                    /* ← 阻塞/崩，不可断言 */
```

**关键技巧**：`usage()` 的横幅把版本号编进了字符串
（`src/usage.c` 用 `src/version.h` 的 `VER` 拼出 `X Color Mixer  V1.07`），
所以"横幅含 `V1.07`"同时是一条版本断言和一条"产物确由本包源码构建"的断言。

**关键技巧 2**：把 display 显式写死到**关闭的回环端口**，即可把工具包初始化失败
变成与环境无关的确定性分支：

```sh
out=$("$BIN" -display 127.0.0.1:99 alpha beta gamma 2>&1)
# rc=1
# In fl_initialize() [flresource.c:995]: …/bin/xcolmix: Can't open display 127.0.0.1:99
```

即使 worker 上 `$DISPLAY` 指向一个可用的 X server，这一条仍然稳定复现，
诊断串里带上端口号就成了"**XForms 代码确实在进程内执行过**"的最强信号。

## 修法 / 测试设计

1. 列出 `main()` 里所有"显示窗口之前就退出"的分支 —— 那就是 headless 上
   可断言的全部面（本例 3 条）。
2. 每条断言打在**可观测契约**上：退出码 + usage/版本横幅，而不是"进程没崩"。
3. 工具包初始化失败分支用 `-display 127.0.0.1:99` 强制触发，断言里匹配端口号。
4. 把会阻塞/崩的路径写进 notes.md 的"不能测"表并附**实测 rc**（本例
   `rc=124` 阻塞 / `SIGSEGV`），评审就不会误读为漏测。
5. 无 `--version`/`--help` 的包，CI 的 L2 冒烟必然记 `skip`/`warn`
   （**非阻塞**）。不要为了让它变绿而给上游加版本开关 —— 那是与任务无关的
   功能新增。
6. 配套：X11 栈的运行期寻库要在配方里声明 `run=True` 依赖，并用
   `LD_PRELOAD` 绝对路径兜底（loader 可能忽略 `LD_LIBRARY_PATH`），
   同 `archives/x/xev/1.2.7` 的做法。

## 先例差异（别照抄 xev）

`xev 1.2.7` 的 `-version` / `--version` / `-help` / 非法选项 4 条路径都**早于**
`XOpenDisplay` 返回，所以它的 4 条断言全是干净退出 0。`xcolmix` 没有版本开关，
只能走拒绝分支（退出码 1）。两者都合法，但 L2 结果不同。

## 适用面

所有基于 X11 / XForms 等工具包的 headless 验证场景：xcolmix、xev 一类 X 应用，
以及任何"CI 上没有 X server"的包。

## 关联

- `archives/x/xcolmix/1.07/notes.md` §6（可测 / 不可测路径表）
- `archives/x/xcolmix/1.07/test_package/test_xcolmix.sh`
- `archives/x/xev/1.2.7/test_package/test_xev.sh`（同形态先例）
