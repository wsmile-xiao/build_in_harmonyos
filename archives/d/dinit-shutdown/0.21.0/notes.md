# dinit-shutdown 0.21.0 适配笔记

## 软件说明

本包是 dinit 0.21.0（上游 davmac314/dinit）的 shutdown 工具集，按发行版拆分方式单独打包：
提供 `dinit-shutdown`、`dinit-halt`、`dinit-poweroff`、`dinit-reboot`、`dinit-soft-reboot`
五个可执行文件（上游把后四个安装为第一个的符号链接，程序按 `basename(argv[0])` 分派动作）。
服务管理器本体（`dinit`/`dinitctl`/`dinit-check`/`dinit-monitor`）不在本包内；运行时工具通过
控制 socket（`/var/run/dinitctl`，上游对非 Linux 平台的默认值）与 dinit 守护进程通信。

## 编译环境

- 构建系统: custom（上游自带 `configure` + 顶层/子目录 `Makefile`，非 autotools/cmake）
- 设备: HarmonyOS PC (aarch64)，`uname -s` = `HarmonyOS`
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/clang++`，target `aarch64-unknown-linux-ohos`）
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（`os=OHOS`、`arch=armv8`、`cppstd=17`）
- make: GNU Make 4.4.1；并行度固定 `-j1`
- 编译日期: 2026-09-11
- 状态: built

## 编译步骤（实际执行）

```bash
# 1. 解包（source() 内由 conan 完成，见“源码修改”节）
#    get(url/filename/sha256, strip_root=True, excludes=["dinit-0.21.0/BUILD"])

# 2. 配置：显式打开 shutdown 工具并加上发行版命名前缀
"$CONFIG_SHELL" ./configure --enable-shutdown --shutdown-prefix=dinit- --disable-strip CXX=<profile 中的 cpp>

# 3. 生成 mconfig.h（mconfig → build/includes/mconfig.h）
make -C build

# 4. 只构建本包交付的目标
make -C src SHUTDOWN_PREFIX=dinit- dinit-shutdown -j1

# 5. 上游单元测试（build() 内执行，create 日志因此带有真实计数）
make -C src check -j1
```

`configure` 在 HarmonyOS 上的平台判定（stdout 摘要）与生成的 `mconfig` 关键项：

```text
# configure stdout
Warning: Platform "HarmonyOS" is unknown!
  ... Known platforms are: Linux, FreeBSD, NetBSD, OpenBSD, Darwin
...
Creating mconfig...
  ... done.

# 生成的 mconfig（节选）
BUILD_SHUTDOWN=yes      # 由 --enable-shutdown 显式打开
SUPPORT_CGROUPS=0       # 非 Linux 平台默认关闭
SUPPORT_CAPABILITIES=0
SUPPORT_IOPRIO=0
SUPPORT_OOM_ADJ=0
SHUTDOWN_PREFIX='dinit-'
SYSCONTROLSOCKET='/var/run/dinitctl'
STRIPOPTS=              # --disable-strip
```

编译进 `build/includes/mconfig.h` 的关键常量：

```c
constexpr static char DINIT_VERSION[] = "0.21.0";
constexpr static char SYSCONTROLSOCKET[] = "/var/run/dinitctl";
constexpr static char SHUTDOWN_PREFIX[] = "dinit-";
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 在 `source()` 阶段失败：Python tarfile 建 `dinit-0.21.0/build` 目录抛 `FileExistsError`（`os.mkdir(targetpath, 0o700)`），构建从未开始 | 上游 0.21.0 release tarball 顶层同时含 `BUILD`（构建说明文档）与 `build/`（构建系统目录）；鸿蒙设备工作区为 HMDFS，**大小写不敏感**（`touch AAA` 后 `stat aaa` 与 `AAA` 同 inode），两个名字解析到同一条目录项 | `source()` 用 `get(..., excludes=["dinit-0.21.0/BUILD"])` 在解包成员层排除该文档文件。`BUILD` 无任何构建规则读取（README 仅以文档链接引用），排除后设备与 CI 解包出的源码树逐字节一致；其余成员全部原样解包 |
| 2 | `make -C src dinit-shutdown` 报 `No rule to make target 'dinit-shutdown'` | `configure` 把 `SHUTDOWN_PREFIX='dinit-'`（**含单引号**）写进 mconfig，make 变量值带引号 → 目标名实际是 `'dinit-'shutdown`；`mconfig.h` 经 shell 去引号后为正确的 `"dinit-"` | make 命令行覆盖变量：`make -C src SHUTDOWN_PREFIX=dinit- dinit-shutdown`，目标名干净且 `mconfig.h` 前缀不变 |
| 3 | 不显式传 `--enable-shutdown` 时根本不构建 shutdown 工具 | `configure` 仅当 `PLATFORM=Linux` 时默认 `BUILD_SHUTDOWN=yes`，而 HarmonyOS PC 的 `uname` 返回 `HarmonyOS`，走 else 分支默认 `BUILD_SHUTDOWN=no` | 显式 `--enable-shutdown` |
| 4 | 若剥离调试符号，产物在设备上加载失败（rc=126） | hnp clang 产物带 `.codesign` 段，`strip`/`llvm-strip` 破坏签名 | 配置期 `--disable-strip`，`package()` 只做 `chmod 0755`，不重签（重签会 SIGSEGV） |
| 5 | `--shutdown-prefix` 若省略，别名行为会静默错位 | 程序按 `basename(argv[0])` 与编译期 `SHUTDOWN_PREFIX` 拼出的 `reboot`/`soft-reboot` 比较；前缀为空而安装名带 `dinit-` 时比较恒不相等，`dinit-reboot` 会退回默认动作（poweroff）。upstream shutdown(8) 明确 `halt`/`poweroff` 别名无特殊语义、默认为 power down，只有 `reboot`/`soft-reboot` 名字参与分派 | 保留 `--shutdown-prefix=dinit-`，并在 test_package 中用 `--help` 的首行（回显自身 argv[0]）逐名断言前缀与安装名一致 |
| 6 | 设备全绿但 CI 必失败：test_package 报 `FileNotFoundError: [Errno 2] No such file or directory: 'dinit-shutdown'` | CI worker 的 python 包用 `os.posix_spawn` 以**裸命令名**spawn，而 `os.posix_spawn` 不做 PATH 搜索；`shutil.which('dinit-shutdown')` 同轮返回成功（PATH 里确有该目录），设备侧 python 走常规 fork/exec 会搜 PATH，故只在本平台 python 形态下失败 | 测试程序一律用 `shutil.which()` 解析出的**绝对路径** spawn 被测产物（`test_dinit_shutdown.py` 的 `run()` 即此实现），不再依赖裸名 + PATH |

## 源码修改

无补丁（`patches_applied: []`）。对上游源码树唯一的处理是解包时排除顶层 `BUILD` 文档文件，
原因见上表第 1 项；该文件不参与构建，被排除后设备与 CI 的构建输入完全一致。

## 依赖版本

无第三方依赖（仅 libc/libc++，编译期与运行期都不依赖其他 conan 包）。

## 验证结果

```text
# 上游单元测试（设备原生，沙箱 HOME）
$ make -C src check -j1
./tests ./proctests ./loadtests ./envtests ./iostreamtests ./cptests
-> 136/136 PASSED（tests 44 / proctests 47 / loadtests 15 / envtests 2 /
   iostreamtests 7 / cptests 21），退出码 0
   与 RUN_TEST 注册数逐文件对账一致（grep -c '^[[:space:]]*RUN_TEST(' = 136）

# 交付产物实际行为（设备真跑，绝不发送关机命令）
$ bin/dinit-shutdown --help        -> 退出码 1，首行 "dinit-shutdown :   shutdown the system"
$ bin/dinit-halt --help            -> 退出码 1，首行 "dinit-halt :   shutdown the system"
$ bin/dinit-poweroff --help        -> 退出码 1，首行 "dinit-poweroff :   shutdown the system"
$ bin/dinit-reboot --help          -> 退出码 1，首行 "dinit-reboot :   shutdown the system"
$ bin/dinit-soft-reboot --help     -> 退出码 1，首行 "dinit-soft-reboot :   shutdown the system"
   （5 个名字的 help 文本一致：-p 为 "(default)"，即默认动作 power down；
     -s 行为 "soft-reboot (restart dinit with same boot-time arguments)"）
$ bin/dinit-shutdown -Z            -> 退出码 1，stderr "Unrecognized command-line parameter: -Z"
$ bin/dinit-shutdown               -> 退出码 1，stderr "connect: No such file or directory"
   （/var/run/dinitctl 无监听；该路径只做 connect，失败即返回，不会触发 reboot(2)）

# 消费者测试程序（test_package/test_dinit_shutdown.py，conan create 内实跑）
$ python3 test_dinit_shutdown.py
RESULT: 48 checks, 48 passed, 0 failed
PASSED 48/48
   （其中 39 条为 5 个交付可执行文件的 CLI 行为断言；
     9 条为**鸿蒙特有**平台契约断言：64 位 LE AArch64 PIE、保留 .codesign 段、
     保留 .symtab（未 strip —— 设备实测 strip 后本平台加载失败 rc=126）、
     编译期控制 socket /var/run/dinitctl、编译期前缀字面量 dinit-reboot/dinit-soft-reboot）
```

`conan-verify`（G0-G4、L2/L4/L5）与 W3 的结果见 `reports/`；采信轮为清缓存后的干净构建；
纯可执行包触发的 G4/L2/L4/L5 跳过路径按流程第 7.2 节人工补测，记录在
`reports/conan-verify-supplement.md`。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/dinit-shutdown` | 约 70 KB | shutdown 工具主体（未 strip，带 `.codesign`） |
| `bin/dinit-halt` | 约 70 KB | 同上，按 argv[0] 分派；上游安装为符号链接，本包按普通文件交付 |
| `bin/dinit-poweroff` | 约 70 KB | 同上 |
| `bin/dinit-reboot` | 约 70 KB | 同上，`-r` 语义 |
| `bin/dinit-soft-reboot` | 约 70 KB | 同上，`-s` 语义 |
| `licenses/LICENSE` | 11 KB | Apache-2.0 |

## 注意事项

1. **别名交付形态**：上游用符号链接安装 4 个别名，本包交付 4 个内容相同的普通文件。程序只按
   `basename(argv[0])` 分派，行为完全一致；这样避免依赖 HMDFS 的符号链接语义，且 conan 在安装
   时本来也会把包内符号链接解引用成普通文件。5 个文件 sha256 相同即为该结论的证据。
2. **控制 socket 路径**：编译期固定为 `/var/run/dinitctl`（上游非 Linux 默认值，与已归档的
   dinit 0.22.0 OHOS 适配一致）。设备上 `/var/run` 目录当前不存在，系统模式下需由部署方创建
   该目录并让 dinit 监听同一路径；也可用 `dinit --socket-path` 指定后，由 dinit 以
   `--use-passed-cfd` 方式调用本工具（`DINIT_CS_FD` 机制）。
3. **未知平台警告**：`configure` 会打印 `Platform "HarmonyOS" is unknown!`。这是上游平台白名单
   未收录 HarmonyOS 的提示，不影响构建（Linux 专有特性因此保持关闭，正是 OHOS 需要的）。
4. **不要执行 `--system`/`-r`/`-h`/`-p`/`-s`/`-k`**：这些会指示服务管理器或直接 `reboot(2)`
   关机。本包的自动化测试只走 `--help`、未知选项和无守护进程的 connect 失败路径。
5. **控制 socket 存在时的测试守卫**：`test_package/test_dinit_shutdown.py` 在检测到
   `/var/run/dinitctl` 存在（有服务管理器在监听）时显式打印 SKIP 并跳过 no-daemon 断言，
   绝不向守护进程发送关机命令。
---

**编译结束**: 2026-09-11 11:05
**最终状态**: built
