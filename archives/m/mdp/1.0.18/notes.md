# mdp 1.0.18 适配笔记

## 软件简介

mdp（Markdown Presenter）是 [visit1985/mdp](https://github.com/visit1985/mdp) 开发的
命令行 Markdown 幻灯片演示工具，基于 ncursesw（宽字符 ncurses）渲染 TUI，
支持 UTF-8、多显示器 header/footer、倒计时等特性。

- 上游：https://github.com/visit1985/mdp
- License：GPL-3.0-or-later（COPYING 为 GPLv3 全文）
- 构建：纯递归 Makefile，无 configure 步骤
- 依赖：ncursesw（宽字符 ncurses）
- 产物：单二进制 `mdp` + man page

## 构建要点

1. **无 configure**：顶层 Makefile 直接编 src/*.c，`CURSES=ncursesw`，
   `LDLIBS=-lncursesw`。Windows 检测 `OS=Windows_NT` 时切 pdcurses（与本平台无关）。
2. **pkg-config**：依赖通过 `pkg-config ncursesw` 传入 CFLAGS/LDFLAGS，
   Conan 的 PkgConfigDeps 生成器可提供 `ncursesw.pc`。
3. **上游无测试**：Makefile 目标仅 all/clean/install/uninstall；
   上游 CI（.github/workflows/c-cpp.yml）仅 `make` + `./mdp -v` 冒烟。
   归档测试策略：消费者测试用程序化 Markdown 输入验证解析（`-d` 调试输出
   headers/slides 计数）与真实终端输出，外加独立 OHOS 验证（ELF64/AArch64/
   musl/.codesign/RPATH/终端运行）。

## 适配要点（鸿蒙 PC aarch64）

- 工具链：clang 15.0.4（aarch64-unknown-linux-ohos）
- ncurses 6.6 归档包提供 ncursesw 库与 curses.h；消费者侧无需额外补丁
- mdp 的 `main()` 开头 `setlocale(LC_ALL, "")`，运行时依赖 locale 与 terminfo：
  本机 TERM=xterm-256color 可用，terminfo 由系统 share/terminfo 提供
- 上游 Makefile 在 `DEBUG=1` 时带 -g；归档构建保持默认 -O3

## 测试

- test_package 用程序化生成的 Markdown 输入驱动 `mdp -d`（调试计数）与
  pty/管道下的 TUI 渲染断言；OHOS 独立测试做 ELF/RPATH/签名/终端验证。
- 两个测试脚本 shebang 为 `#!/usr/bin/env bash`（`set -euo pipefail`）；
  test_package/conanfile.py 按 CONFIG_SHELL → SHELL（basename 须为 bash
  且可执行）→ `shutil.which("bash")` 顺序解析 bash 后显式执行脚本，
  不依赖 shebang 碰巧存在；三者皆不可用时抛 ConanException（fail-closed），
  不回退 /bin/bash 或任何硬编码绝对路径。
- test_ohos.sh 中的 `/data/usr/share/terminfo` 是 terminfo 数据库位置探测
  候选（运行时数据路径，非执行路径）；Test 4 对二进制的字符串扫描
  （`.conan2/p`、`/conan/`）是宿主路径泄漏检测模式——断言产物不携带
  构建机路径，属禁止泄漏检测而非执行路径。脚本中不存在任何
  硬编码宿主执行路径。
- 见 test_package/MANIFEST.yml 的断言清单。

## 知识沉淀决策

- 适配路径：路径 A（基础适配）+ 路径 B（知识沉淀，两条草稿均通过四条件验证）。
- 知识库全量查重（graph 542 条 + drafts + index.tsv + git log --all + 全部 refs
  与 worktree 未提交文件）：无"运行时 terminfo 数据库搜索路径"条目
  （E031 为 SELinux /proc、E121 为 utmpx 链接、历史上 unxip/mariadb 均为
  链接期符号缺失），无"TUI stdin 内容与 /dev/tty 按键分离须 pty 双通道
  测试"条目。
- 草稿 1（DRAFT-E568，musl terminfo 搜索路径）：真实失败（pty 内无 TERMINFO 时 76 字节
  退出 `cannot initialize terminal type`；设置后 ESC[?1049h 交替屏渲染成功，
  正/反向均实测复现），新根因 + 可复用方案（test_ohos.sh Test 6 落地）。
- 草稿 2（DRAFT-E569，pty 双通道测试）：真实失败（`printf | mdp -d -` 因 freopen
  "/dev/tty" 失败退出 1，上游 main.c 无条件 freopen），新根因 + 可复用方案
  （test.sh Test 4 落地，纯管道反向复现）。
