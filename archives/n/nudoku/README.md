# nudoku

## 简介

nudoku 是一个基于 ncurses 的数独（TUI）游戏，支持按难度生成谜题、自动求解、提示、撤销、着色高亮等。

- **GitHub**: https://github.com/jubalh/nudoku
- **License**: GPL-3.0

## 已编译版本

- **版本**: 5.0.4

## 编译方式（OHOS）

上游使用 autotools，但官方 GitHub 源码包是 git 快照，**仅含 configure.ac**（无预生成 `configure`/`Makefile.in`/`config.guess`）。由于项目仅两个翻译单元——`src/main.c`（ncurses UI）与 `src/sudoku.c`（纯 C 求解器，不依赖 ncurses），本配方直接用 Conan 提供的 clang 编译，链接系统预装静态 ncurses（libncursesw.a），并将求解器编为 `libnudoku.a` 供 test_package 调用真实求解器 API。

```bash
PREFIX=/storage/Users/currentUser/usr/local   # 系统静态 ncurses
clang -O2 -DVERSION=\"5.0.4\" -I$PREFIX/include -I$PREFIX/include/ncursesw \
  -c src/sudoku.c -o sudoku.o
llvm-ar rcs libnudoku.a sudoku.o
clang -O2 -DVERSION=\"5.0.4\" ... -c src/main.c -o main.o
clang main.o -L. -lnudoku -L$PREFIX/lib -l:libncursesw.a -o nudoku
```

### OHOS 适配要点

- `VERSION` 宏上游由 autotools 注入，手动编译需 `-DVERSION="5.0.4"`
- ncurses 为系统预装静态库（libncursesw.a），wide-char 版头文件在 `ncursesw/` 子目录
- 无需源码补丁

详见 `5.0.4/notes.md`。
