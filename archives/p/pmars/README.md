# pMARS

可移植的 **Core War** 模拟器（Memory Array Redcode Simulator），实现 ICWS'94 Redcode
标准并带上游扩展指令（`NOP/SEQ/SNE`、`*`、`{`、`}` 及 P-space 扩展）。两个或更多用
Redcode 汇编语言写的"战士"在模拟内存（core）里互相攻伐，由模拟器按指令周期推进，
最后按存活/得分判定胜负。

上游：<http://www.koth.org/pmars/>（GPL-2.0-or-later）。

## 本包的显示形态

发布的是 **终端 curses 显示**变体（`-DCURSESGRAPHX`）。上游默认 Makefile 的 X11
图形变体（`-DXWINGRAPHX` + `-lX11`）在 HarmonyOS PC 上没有对应显示服务，已在**编译期**
关闭（不改源码、不引入平台宏），细节见 `0.9.5/notes.md`。

## 用法

```sh
pmars [options] file1.red [file2.red ...]     # 默认 8000 core、1 回合
pmars -b -r 3 warriors/sonofvain.red warriors/excalibur.red
pmars -A warriors/sunset.red                  # 只装配，不打（;assert 在此求值）
```

随包数据在 `res/` 下：`res/warriors/*.red`（6 只战士，含上游作者写的系统一致性程序
`validate.red`）、`res/config/*.opt`（KotH 风格选项集）、`res/doc/pmars.txt`（手册）。

注意：进入核心画面需要能解析终端类型（terminfo）。经 conan 运行环境
（`conanbuild/conanrun`）执行时由 `ncurses` 依赖自动提供；直接裸执行时需自备
`TERMINFO`/`TERMINFO_DIRS`，否则 pmars 会以
`ncurses: cannot initialize terminal type` 退出。

`pmars` 没有 `--version`；脚本化取版本用退出码探针：

```sh
pmars -Q 1000 >/dev/null 2>&1; echo $?   # 95 == PMARSVER of 0.9.5
```

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.9.5 | 已适配 | 首个 HarmonyOS PC 适配版本；含 opaque WINDOW 访问器补丁 |
