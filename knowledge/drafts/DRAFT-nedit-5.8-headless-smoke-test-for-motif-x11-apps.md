# 没有 X server 的时候，怎么证明一个 Motif 程序是能跑的

> Draft: DRAFT-nedit-5.8-headless-smoke-test-for-motif-x11-apps
> Stem: `nedit-5.8-headless-smoke-test-for-motif-x11-apps` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-nedit-5.8-headless-smoke-test-for-motif-x11-apps
- **严重度**: 2
- **类别**: testing|x11|motif|headless|runtime-link
- **触发工具**: conan|x11|motif|test
- **阶段**: testing

## 错误特征

```
nedit: error while loading shared libraries: libXm.so.4:
       cannot open shared object file: No such file or directory
```

或者，反过来的那一种：

```
Error: Can't open display: (null)
```

第一种是**动态链接没解析到**（依赖图的 libdir 没进 `LD_LIBRARY_PATH`，或
产物没签名导致 `PermissionError: [Errno 13]`）；第二种是**真的去开显示了**，
worker 上没有 X server。两者的修法完全不同，而一句笼统的"图形程序跑不起来"
会把它们混在一起。

## 根因分析

CI worker 上没有 X server，"启动程序看它能不能跑"这条默认验收路径直接走不通。
但图形程序里往往藏着一条**不依赖显示**的查询路径，nedit 5.8 里两个二进制都有：

`source/nedit.c` 先开显示，只在**失败之后**才检查版本开关：

```c
TheDisplay = XtOpenDisplay(context, NULL, APP_NAME, APP_CLASS, NULL, 0, &argc, argv);
unmaskArgvKeywords(argc, argv, protectedKeywords);
if (!TheDisplay) {
    /* Respond to -V or -version even if there is no display */
    for (i = 1; i < argc && strcmp(argv[i], "--"); i++)
        if (0 == strcmp(argv[i], "-V") || 0 == strcmp(argv[i], "-version")) {
            PrintVersion();
            exit(EXIT_SUCCESS);
        }
    fputs("NEdit: Can't open display\n", stderr);
    exit(EXIT_FAILURE);
}
```

`source/nc.c` 更早——在 `XtOpenDisplay` **之前**就处理命令行：

```c
/* Process the command line before calling XtOpenDisplay, because the
   latter consumes certain command line arguments that we still need */
commandLine = processCommandLine(argc, argv);
...
TheDisplay = XtOpenDisplay(...);
if (!TheDisplay) { XtWarning("nc: Can't open display\n"); exit(EXIT_FAILURE); }
```

### 关键：判断"开关能否存活"必须读选项表，不能凭直觉

nedit 的主流程里，`-V` 到达上面那个循环之前要穿过两道会改写 argv 的逻辑：

1. `CreatePreferencesDatabase()` → `XrmParseCommand(&db, opTable, nOptions, appName,
   argcInOut, argvInOut)`。这会**真的修改 argc/argv**——但只会移除
   **选项表里认得**的参数。查 `source/preferences.c` 的 `OpTable`：`-wrap`、
   `-rows`、`-svrname` … **没有 `-V`**，所以它原样留下。
   （nc 的 `OpTable` 同样只有 `-ask/-noask/-svrname/-svrcmd/-wait/-timeout`。）
2. `maskArgvKeywords()` 把 `-iconic/-geometry/-title` 之类的首字符 `-` 换成空格，
   让 `XtOpenDisplay` 看不见它们，之后再 `unmaskArgvKeywords()` 还原。
   `-V` 不在保护列表里，不受影响。

也就是说，"`-V` 能不能在无显示时生效"这个问题，答案只能从**代码里三处**
（OpTable、protectedKeywords、pre-display 分支）读出来。凭"老程序一般都支持"
猜，迟早会踩空。

### 关键：正向断言不足以证明它真的是 X 客户端

如果测试只断"`-V` 打印了版本并退出 0"，那么一个把 `main()` 写成
`if (argv[1] == "-V") puts("NEdit 5.8");` 的 **stub** 也能通过。
所以需要**反向断言**：同一个二进制，不带 `-V`、且没有 `DISPLAY` 时，**必须
失败**。这才会强制它走到 `XtOpenDisplay`，从而证明上面那条正向路径是
"刻意的提前应答"，而不是"根本不打开显示"。

## 解决方案

**主方案**: find-pre-display-query-path-and-assert-both-directions

```python
def run(command, *args):
    env = dict(os.environ)
    env.pop("DISPLAY", None)          # 主动摘掉，不假设环境干净
    return subprocess.run([command, *args], capture_output=True,
                          text=True, errors="replace", timeout=120, env=env)

# 正向：版本路径可用（退出码 0 + 版本串）
for option in ("-V", "-version"):
    result = run(nedit, option)
    assert result.returncode == 0
    assert "NEdit 5.8" in result.stdout + result.stderr

# 链接自证：输出里那行编译期/运行期信息
assert "With Motif:" in run(nedit, "-V").stdout

# 反向：没有显示时必须失败
result = run(nedit)
assert result.returncode != 0
assert "Can't open display" in result.stdout + result.stderr
```

四点补充：

1. **`os.environ.pop("DISPLAY")` 要主动做。** worker 是否导出 `DISPLAY` 不由配方
   决定；一旦某个 worker 恰好带着 `DISPLAY`，测试会去连一个半死的 X server。
2. **动态链接的图形程序要把整张依赖图的 libdir 前缀进 `LD_LIBRARY_PATH`。**
   `VirtualRunEnv` 只覆盖**声明了 runenv 的节点**；`libXm.so.4` 的
   `DT_NEEDED`（libXt / libXext / libX11 / libSM / libICE）不一定都在里面：

   ```python
   libdirs = []
   for node in self.dependencies.values():
       if not node.package_folder:
           continue
       for libdir in node.cpp_info.aggregated_components().libdirs:
           libdirs.append(libdir if os.path.isabs(libdir)
                          else os.path.join(node.package_folder, libdir))
   prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(
       ":".join(dict.fromkeys(libdirs)))
   ```

3. **用绝对路径从包缓存执行产物**，不要走 `PATH`。L1e 会把 `bin/` 移走再重跑，
   如果测试靠 `PATH` 找到了别处的同名程序，L1e 就会判定"测试不依赖被测包"。
4. **别用 `/bin/sh` 启动 ELF。** OHOS 的 `/system/bin/sh`（mksh）不能执行
   ELF 二进制；本包用 `sys.executable` 跑一个 Python 脚本
   （`test_nedit.py`），既避开 shell，也避开 `echo` 式假测试（L1d）。

顺带值得一提的第三条断言：nedit `-V` 输出里的 `"With Motif:"` 行由
`source/help.c:getBuildInfo()` 拼出，包含 `XmVERSION/XmREVISION/XmUPDATE_LEVEL`。
它证明**编译期头文件**与**运行期链接的 libXm** 是同一个版本——这是一个
比"程序没崩"强得多的证据。

## 验证

```sh
# 静态确认 pre-display 路径存在
grep -n "Respond to -V or -version even if there is no display" source/nedit.c
grep -n "Process the command line before calling XtOpenDisplay" source/nc.c
# 确认 -V 不在 XrmParseCommand 的选项表里（否则会被吃掉）
sed -n '/static XrmOptionDescRec OpTable/,+12p' source/nc.c

CI_PACKAGES="archives/n/nedit/5.8" zsh ci/conan/build_and_test.sh
# test_package 应报 30/30；日志中不应出现任何 X server 连接尝试
```

## 关联条目

- 前置本仓库条目 `DRAFT-nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets`：
  因为构建期不能执行产物（顶层 make 会在末尾执行刚链接的二进制），验证只能
  整体搬到 `test_package`，这正是本条要解决的"没有 X server 怎么办"。
- 相近条目 `DRAFT-openvi-7.9.33-nonautotools-argv0-mode-musl-pty-ncurses-override`：
  同为"非 autotools、终端/图形程序在 OHOS 上的可运行性验证"，那条的核心是
  terminfo/PTY，本条的核心是 X display。
