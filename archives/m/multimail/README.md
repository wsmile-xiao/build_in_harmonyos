# multimail

离线邮件包阅读器 MultiMail（Blue Wave / QWK / OMEN / SOUP / OPX），curses 交互界面。

- 上游：https://github.com/wmcbrine/MultiMail（tag 0.52）
- 主页：http://wmcbrine.com/mmail/
- 许可证：GPL-3.0-or-later
- 类型：命令行工具（tool），产物 `bin/mm` + 手册 `share/man/man1/mm.1`

## OHOS 适配

- 纯 Makefile 构建，无 configure；`make -j1 DEBUG=Y`（跳过 `strip` 后处理）。
- `CURS_DIR`/`LIBS` 指向 `ncurses/6.6`（上游默认 `-lcurses` 在 OHOS 不可用）。
- 不用上游 `make install`（`install -s` 依赖 strip，`ln` 硬链接在 HMDFS 不可靠），改为手动拷贝。
- 上游无测试套件；消费者测试见 `0.52/test_package/`。

## 依赖

- `ncurses/6.6`（curses 头文件与 `libncursesw`）

## 参考

- 源码仓库：https://github.com/wmcbrine/MultiMail
- 各版本详情见 `0.52/notes.md`
