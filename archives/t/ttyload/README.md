# ttyload

终端里的系统负载均值曲线图：把 1 / 5 / 15 分钟负载画成一张随时间向左滚动的
ASCII 字符图，跑在任何 ANSI 终端上，**不需要 curses，也不需要任何外部库**
（纯 libc + 直接输出转义序列）。适合没有 X、只能登控制台或远程 shell 的机器。

## 上游

- 主页：<http://www.daveltd.com/src/util/ttyload/>（作者 David Lindes，1996-2011）
- 源码仓库：<https://github.com/lindes/ttyload>
- 许可：ISC（'LICENSE' 自述为 "a modified version of the ISC License"）
- 语言构成：3 个 C 文件（'ttyload.c' / 'archtest.c' / 'loader.c'，共 629 行）
  + 每个平台一对 'arch/<OS>/{getload.c,terminfo.c}'；'loader.c' 上游默认不建。

## 本包构建产物

只有一个可执行文件 'ttyload'（无库、无头文件）：

| 文件 | 说明 |
|---|---|
| 'bin/ttyload' | 主程序 |
| 'LICENSE' | 许可证 |

用法：'ttyload'（直接跑，Ctrl-C 退出）；'ttyload -m' 单色模式；
'ttyload -i 1' 1 秒刷新；'ttyload -r rows -c cols' 手工指定终端尺寸；
'ttyload -h' 帮助、'ttyload -v' 版本。
注意上游把 '-v'/'-h' 实现成"打印后走 usage 分支并以 1 退出"，退出码不是失败信号。

## HarmonyOS PC 适配要点

上游用 'uname -s' 的结果去拼**架构目录白名单**
（'OBJS = arch/${ARCH}/getload.o arch/${ARCH}/terminfo.o'），而 tarball 只带
FreeBSD / IRIX / Linux / SunOS 四个目录。HarmonyOS PC 上 'uname -s' = 'HarmonyOS'，
不改源码 'make' 会直接报 'No rule to make target 'arch/HarmonyOS/getload.o''。

'patches/0001-Makefile.patch' 用上游**自己的**"架构互仿"机制（'ARCHLINKS'，
'arch/Darwin'、'arch/Isilon-OneFS' 就是这么 'ln -s FreeBSD' 来的）把
'arch/HarmonyOS' 映射到 Linux 后端。映射依据是实测：'arch/Linux/getload.c'
只读 '/proc/loadavg'，'arch/Linux/terminfo.c' 只用 'ioctl(TIOCGWINSZ)'，
两者在 HarmonyOS PC 上均可用（详见版本目录 'notes.md'）。

其余：构建机只有 OHOS SDK clang（无 'gcc'/'cc'），故 'CC' 由 Conan 侧解析后作为
make 命令行变量传入；上游 '-Werror' 在 OHOS sysroot 自身发出的 '#warning' 下必挂，
保留 '-pedantic -Wall'、仅降级 '-Werror'；不跑上游 'make test'
（它是永不退出的交互式绘图），改在 'test_package' 里有界执行同一程序、另加 '-m' 单色选项
（实物 'ttyload -m -i 1'）并做 4 条断言。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.5-20131024-gitf949537 | built | 首次适配 HarmonyOS PC；上游 'Version' 文件实物内容为 0.5.3 |

版本串两种形态并存且**不做归一化**：平台/归档目录用连字符
'0.5-20131024-gitf949537'，tarball 与解包目录用加号 '0.5+20131024+gitf949537'。
