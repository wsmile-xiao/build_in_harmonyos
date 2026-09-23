# ne (the nice editor)

ne 是一个免费（GPL）的 Unix 终端文本编辑器，基于 POSIX 标准，对新手友好，同时对高手强大且完全可配置。

- 上游：https://github.com/vigna/ne（官网 ne.di.unimi.it 重定向至此）
- 特性：UTF-8 支持、语法高亮、无限撤销/重做、宏录制、大文件编辑、正则搜索替换

## 鸿蒙 PC 适配要点

1. **生成源码托管源**：上游 `hash.c/names.c/enums.h/help.c/ext.c/version.h` 等 9 个文件是 `makeinfo -D autohelp ne.texinfo` + `perl info2src.pl` 的生成物（`src/.gitignore` 中列出），tag tarball 不含它们。CI 环境无 texinfo，故预生成后托管在本仓库 `ne-src-raw` 分支（conandata `generated_sources` 第二源，先例 clp-src-raw；`source()` 下载 sha256 校验后拷入 `src/`）。重新生成方法见 notes.md。
2. **terminfo 运行时**：OHOS `/usr/share/terminfo` 仅极简条目。本包 `package()` 从 conan `ncurses/6.4` 复制完整 terminfo 数据库（2868 条）到 `share/terminfo`，`package_info` 定义 `TERMINFO`/`TERMINFO_DIRS` 环境变量。
3. **静态链接**：链接 conan `libncursesw.a`（ncurses 配方 `--without-shared` 构建），单二进制分发。
4. **非 tty 行为**：ne 在 stdin 非 tty 时 `freopen("/dev/tty")` 失败直接 abort——脚本化使用需 pty 或确保有终端。

## 用法

```sh
ne file.txt                # 交互编辑
ne --macro cmds.macro f    # 执行宏后退出（非交互自动化）
ne --ansi                  # 使用内置 ANSI 终端描述（无 terminfo 时）
```
