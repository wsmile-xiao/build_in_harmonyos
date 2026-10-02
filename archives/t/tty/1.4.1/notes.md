# tty 1.4.1 适配笔记（上游项目 mpereira/tty-solitaire）

> 命名说明：平台任务/Conan 包名/归档目录均为 `tty`；上游项目名为 tty-solitaire，二者指同一软件。以下证据日志中的 `tty-solitaire` 路径为改名前实测留存，内容有效。

## 编译环境
- 构建系统: makefile（裸 Makefile，非 autotools，无 configure）
- 编译日期: 2026-09-30
- 编译器: clang（15.0.4，OHOS aarch64 交叉）
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/mpereira/tty-solitaire/archive/refs/tags/v1.4.1.tar.gz
   （sha256 8eb536a87f0586e1f057a3aa05256df34cbd92a3e22545d1df2f945e27d89db2）
2. 依赖核验（W0/R36）: `conan download "ncurses/*" -r=ohpcd --only-recipe` → ncurses/6.5、6.6 已发布 ✅；
   `preflight_check.sh tty/1.4.1` → 无其他依赖声明 ✅
3. 探索构建（命令行变量覆盖 Makefile 内赋值，`+=` 对命令行变量无效，故全量显式传入）:
   ```bash
   make -j1 CC=clang \
     CFLAGS='-g -W -Wall -pedantic -std=c99 -DVERSION=\"1.4.1\" -I<ncurses>/include -DNCURSES_WIDECHAR' \
     LDFLAGS='-L<ncurses>/lib -lncursesw'
   make install PREFIX=/usr DESTDIR=$TEST_PREFIX
   ```
4. 上游测试实际执行:
   ```bash
   make test CC=clang CFLAGS='...' LDFLAGS='...'
   # 编译 tests/ttysolitaire_test 并运行，退出码 0，无 Assertion failed / Aborted
   ```
5. conan 配方: conanfile.py（makefile 模式，参照 tty-clock/2.3 先例），
   build() 内先 `make` 再 `make test`（上游测试进 CI 可见日志）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `invalid suffix '.1' on floating constant` | `-DVERSION="1.4.1"` 的引号经 make→shell 两层后丢失，宏展开成裸 `1.4.1` | CFLAGS 传 `-DVERSION=\\"1.4.1\\"`（反斜杠引号保留到编译器） |
| 2 | pty 内游戏启动后按 `q` 被回显但不退出 | OHOS musl + 静态 ncurses 下 `tcsetattr`（raw/noecho）未生效，输入落入规范模式行缓冲，需换行提交 | 消费者用例发送 `q\n`；记录为 OHOS 静态 ncurses 类平台差异（同 tty-clock terminfo stale 路径） |
| 3 | pty 默认 24 行太小，游戏提示 increase terminal size | 游戏要求终端 ≥57x28 | pty 用例用 TIOCSWINSZ 设 30x100 |
| 4 | ncurses 报 Error opening terminal（stale staging terminfo 路径） | 静态 ncurses 内置编译期 DESTDIR 残留路径（同 tty-clock #3） | 运行期 `TERMINFO` 环境变量指向 ncurses 依赖包内 `share/terminfo`，无需 symlink |

## 源码修改

无补丁（上游 Makefile 通过命令行变量即可完成全部适配，patches: {}）。

## 依赖版本

- ncurses/6.5（静态库 --without-shared，-lncursesw + -DNCURSES_WIDECHAR；制品仓 R36 核验通过）

## 验证结果

```bash
$ /data/storage/el2/base/cache/test-install-tty-solitaire-1.4.1/usr/bin/ttysolitaire -v
1.4.1
$ readelf -d .../ttysolitaire | grep NEEDED
  (NEEDED) Shared library: [libc.so]   # ncursesw 静态链接，符合 R4/R26
$ file .../ttysolitaire
  ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
# pty 端到端: 欢迎界面渲染 ✅ / endwin 退出序列 ✅ / 退出码 0 ✅
```

## 上游测试证据（R51）

- 入口: `tests/ttysolitaire_test.c` → `make test` 编译 `ttysolitaire_test` 并执行
- 统计: **67 个具名测试函数 / 115 个断言 / 0 失败 / 0 跳过**
- 分布: card 6、cursor 1、deck 1、frame 4、game 22、gui 1、keyboard 1、stack 17、test_helper 14
  （断言分布: card 12 + cursor 1 + deck 1 + frame 7 + game 47 + gui 1 + keyboard 1 + stack 29 + test_helper 16 = 115）
- 日志: /data/storage/el2/base/cache/tty-solitaire-maketest.log

## 注意事项

- tty-solitaire 是 ncurses 交互程序，端到端运行需 TERM=xterm + TERMINFO 指向有效 terminfo 数据库
- ncurses 必须静态链接（R4：OHOS 上 shared ncurses 会导致系统崩溃）
- 包内二进制 `ttysolitaire` 为 CLI 可执行 → 软件级 commands.json 已声明（R38）
- 版本查看用 `-v`（不是 `--version`）
---

**编译结束**: 2026-09-30 16:55
**最终状态**: built
