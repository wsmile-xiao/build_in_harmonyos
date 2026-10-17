# mdp-src 1.0.18 适配笔记（HarmonyOS PC · 裸 Makefile + 静态 ncursesw）

## 定位
- 产出 CLI 工具 bin/mdp（curses 全屏 Markdown 演示器）+ man 手册页。
- 上游递归 Makefile（顶层 + src/），无 configure、无测试目标；依赖 ncursesw（宽字符 curses）。
- 归档 ncurses 为静态包（libncursesw.a，避免遮蔽系统 libncursesw.so.6），mdp 二进制内嵌 curses，
  运行期无需库路径。

## 源
- https://github.com/visit1985/mdp/archive/refs/tags/1.0.18.tar.gz
- sha256: 36861161513c508c0589014510cdafd940a6e661e517022a3bea48ecf8d5fac4

## W0/W0b
- preflight_check.sh：初配无依赖声明通过；配方写入 ncurses/6.6 后复查，依赖已发布，通过。
- 历史归档：archives/m/ 无 mdp 历史配方（本包为首配）；archives/n/ncurses/ 有 6.4/6.5/6.6 三版，
  选用最新 6.6。
- lang-preflight：task=cpp，detected=c（c 7 文件 100%），构建系统 make，通过。

## 探索构建（真机 conan create 全量验证）
1. 链接行顺序坑（本包关键点）：顶层 Makefile 的链接规则为
   `$(CC) $(OBJECTS) $(LDLIBS) $(CFLAGS) $(LDFLAGS) -o mdp` —— LDLIBS 位于 LDFLAGS **之前**，
   若把 -L 放进 LDFLAGS，链接器自左向右扫描时 `-lncursesw` 出现在 `-L` 之前，必然找不到库。
   解法：把 `-L<ncurses libdir> -lncursesw` 整体作为 LDLIBS 传给 make（LDLIBS 为硬赋值，命令行
   变量可覆盖），顺序在变量内部自控。
2. CFLAGS 用 `?=` 定义、命令行变量优先级更高且经 MAKEFLAGS 传给 src/ 子 make，显式传
   `CFLAGS="-O2 -I<ncurses includedir>"` 即可同时作用于编译与链接，无需补丁。
3. package() 手工 copy bin/mdp + share/man/man1/mdp.1 + COPYING（licenses/），chmod 755 后
   走 binary-sign-tool ELF 自签（签名前后行为一致）。

## 上游测试账本（R51 五维）
- N_static = 0：上游无自动化测试——顶层 Makefile 目标仅 all/clean/install/uninstall（src/ 仅
  all/clean），源码树仅 src/*.c 与 include/*.h，无任何测试源文件（清点证据，不虚构）。
- N_registered = N_executed = 0（如实申报）。
- 消费者测试（test_package）1 程序 / 2 断言：①`mdp -v` 断言精确版本横幅 "mdp 1.0.18" 且退出码 0；
  ②缺失输入文件断言非零退出码（错误路径）。未用 curses 交互路径（无 TTY 时无法运行全屏 UI），
  消费者以非交互代码路径驱动被测二进制。

## 路径 B 判断
- 判定：不成立。候选知识"链接行 -L 位置陷阱"与 makefile 检查清单既有 R33 条目同族（查重命中），
  且属单配方内的 makefile 调参；无新错误签名、无跨仓库复用增量。按纯 A 申报。

## 状态
built —— conan create 真机验证通过（版本横幅断言 + 错误路径断言全绿）。

---
**编译结束**: 2026-09-18 03:05
**最终状态**: built
