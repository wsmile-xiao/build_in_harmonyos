# lr

`lr` 是一个递归列出文件的命令行工具，作者把它定位为 `ls(1)`、`find(1)`、`stat(1)`、`du(1)` 四者常用能力的合集：一次遍历整棵目录树、按名称排序输出相对当前目录的路径、用 C 风格表达式过滤、按需自定义输出格式、并能在遍历过程中计算目录大小。上游 <https://github.com/leahneukirchen/lr>（作者 Leah Neukirchen，MIT 许可）。

## 功能概述

- 递归遍历：默认深度遍历整棵树并按名称排序；`-d` 不进入目录、`-1` 只下一层、`-U` 遍历时直接输出（不排序）、`-W` 按名称排序后边遍历边输出、`-B` 广度优先、`-D` 深度优先（同时计算 `entries`/`total`）
- 过滤表达式（`-t`）：`type`/`mode`/`size`/`depth`/`uid`/`gid`/`inode`/`links`/`mtime` 等属性配合 `== = != < <= > >=`、`&& || ! ? :`、glob（`~~`）、POSIX ERE（`=~`）、大小写不敏感比较（`===`），以及 `prune`/`skip`/`print`/`color N` 动作；`-e REGEX` 是按文件名的快速过滤
- 输出格式：`-0`（NUL 分隔）、`-F`（类型标记）、`-l`（`ls -l` 风格长格式，配合 `-TA/-TC/-TM` 选择时间戳、`-h` 人类可读大小）、`-S`（stat 风格）、`-f FMT`（自定义 `%p %P %f %s %S %b %k %d %D %R %i %n %l %m %M %y %u %g %U %G %e %t %Y %x %Cy-%Cm-%Cd` 等）
- 其他：`-Q`/`-P` 文件名引用（shell 与 `$'...'` 语法）、`-G`/`-X` 颜色与 OSC 8 超链接（遵循 `$NO_COLOR`）、`-s` 去掉命令行前缀、`-x` 不跨文件系统、`-H`/`-L` 符号链接跟随策略、参数 `-` 从标准输入读取文件名
- 退出码有语义：顶层参数无法 `stat` 时为 1，用法错误为 2，正常为 0

## 依赖关系

- 编译依赖：无。单文件 ANSI C，只用 libc 与 POSIX 头（`dirent.h`/`fnmatch.h`/`regex.h`/`sys/stat.h`/`pwd.h`/`grp.h`/`mntent.h` 等）
- 运行依赖：无。`-l` 的 `#`/`+`/`@` 附加标记需要宿主支持 `listxattr(2)`（Linux/OHOS 路径），缺失时该列退化为空，不影响其余功能

## OHOS 适配

- 零补丁：上游源码未经任何修改即可用 OHOS SDK clang 15（`aarch64-linux-ohos`）交叉编译，产物为 PIE ELF64 可执行文件；无平台宏注入
- 不依赖 `fts(3)`：lr 自带 `opendir/readdir` 遍历，避开了 musl 对 `fts.h` 支持不完整这一常见障碍
- Linux 代码路径在 OHOS 上真实可用：`sys/xattr.h` 的 `listxattr`/`llistxattr`（`-l`、`%x`）与 `mntent` 的 `scan_filesystems`（`%Y`、`fstype` 过滤器）在 HarmonyOS PC 上实测工作，`%Y` 报告 `hmdfs`
- 安装：上游 `make install` 会写入 `PREFIX`（默认写死为系统前缀）且依赖 `install(1)`；配方 `package()` 改为直接复制 `bin/lr`、`share/man/man1/lr.1`、`share/zsh/site-functions/_lr` 到包目录，不触碰任何共享系统前缀
- 上游无正式测试用例（Makefile 只有 `all/clean/install/FRC` 目标）；各适配版本通过 test_package 补全真实消费者行为与 HarmonyOS ELF/ABI 专项验证，其中 2.0.1 共执行 36 项检查
- 与 Linux 的差异：`-l` 的属主/组列显示 OHOS 的 uid/gid 与其名称；HMDFS 不强制 `chmod(2)` 的只读语义，依赖权限拒绝的行为在设备上与 Linux 不同（与 lr 无关）

## 参考资料

- 上游仓库：<https://github.com/leahneukirchen/lr>
- 手册：各版本包内 `share/man/man1/lr.1`；`-h` 是“人类可读大小”开关而非帮助选项
- zsh 补全：包内 `share/zsh/site-functions/_lr`
- 使用说明与 Rosetta stone（`ls`/`find` 对照写法）：上游 `README.md`

## 版本

- `2.0.1` — 适配 HarmonyOS PC，零源码补丁、仅依赖 libc；test_package 36/36 通过；详见 [2.0.1/notes.md](2.0.1/notes.md)
- `1.5.1`（2020-01-18）— 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），零补丁、零依赖；详见 [1.5.1/notes.md](1.5.1/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/lr` | 主程序（arm64 ELF，PIE） |
| `share/man/man1/lr.1` | man 手册 |
| `share/zsh/site-functions/_lr` | zsh 命令补全脚本 |
