# pal

文本模式日历与日程管理器（curses + readline）。按月打印公历网格，并在日历上/下列出
节日、生日、纪念日等事件；支持 `.pal` 日历数据文件、HTML/LaTeX 导出与交互式录入。

- 上游主页：<https://palcal.sourceforge.net>
- 许可证：GPL-2.0-or-later（源码树 `COPYING` 为 GPL-2 正文，各 `.c` 头注明"any later version"）
- 构建系统：裸 Makefile（顶层 `Makefile` + `src/Makefile` + `src/Makefile.defs`，无 configure/CMake/meson）

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.4.3 | 见 `0.4.3/manifest.yaml` | HarmonyOS PC aarch64，产物 `bin/pal` |

## 交付面

`bin/pal` 可执行文件 + `etc/pal.conf` 全局配置模板 + `share/pal/*.pal` 日历数据
+ `share/man/man1/pal.1` 手册页。

`src/convert/` 的 `ical2pal` / `pal2ical` 需要 libical、`vcard2pal` 是 awk 脚本，
本轮**不进交付面**（范围决策，理由见 `0.4.3/notes.md`）。

## HarmonyOS 适配要点

1. `Makefile.defs` 全用普通 `=` ⇒ make 忽略环境变量 `CFLAGS/LDFLAGS`，旗标必须整体注入。
2. ncurses 制品只有宽字符库（`libncursesw.a`，无 `libncurses.a`），且 `gettext` 需要 `-lintl`。
3. `manage.c` 使用 readline 私有宏 `Function`，clang 下需换成公开的 `rl_hook_func_t *`。
4. **OHOS 上被 strip 过的 ELF 不可执行**（`execve` → `Operation not permitted`，rc 126）
   ⇒ 上游链完即 strip 必须关掉，而不是事后重签。
5. 设备无 `install` 命令且非 root，上游 `make install` 不可用 ⇒ 配方自己拷交付物。

详见 `0.4.3/notes.md`。
