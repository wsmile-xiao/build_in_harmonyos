# worklog

基于 ncurses 的工时/计时表终端程序。读取项目配置文件（每行 `<键>:<项目名>`），
运行一个走秒的时钟，把时间按项目分别追加到 `<日志文件>` 和
`<日志文件>.<项目键>` 两级账本中。

- 上游：https://github.com/atsb/worklog
- 版本：2.1（tag `Worklog-2.1`）
- 许可证：public domain（原作者 Truxton King Fulton II 声明）
- 依赖：`ncurses/6.6`（OHOS 侧静态）

## 用法

```
worklog [<项目配置文件> [<日志文件>]]
worklog -h            # 打印用法
```

无参数启动时，程序会 `chdir` 到 `$HOME`，并使用默认配置文件 `projects`
与默认账本 `worklog_time.log`。

## 本仓适配说明

- 纯 Makefile 构建（无 configure/autotools），无 `make check` 目标。
- 交叉编译器经 `self.conf` 注入（OHOS clang），补丁把上游硬编码的 `gcc`
  改为 `$(CC)`。
- 上游默认 `-lncurses`；OHOS 侧 `ncurses/6.6` 只产出宽字符静态库
  `libncursesw.a`，故 `LIBS` 由配方覆盖为 `-lncursesw`。
- 运行期提示：ncurses 静态链接会带入构建期 terminfo 路径，若在
  `$TERMINFO` 未指向有效目录时报 `Error opening terminal`，设置
  `TERMINFO=<ncurses prefix>/share/terminfo` 即可。
